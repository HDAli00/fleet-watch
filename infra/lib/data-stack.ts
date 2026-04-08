import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as kinesis from "aws-cdk-lib/aws-kinesis";
import * as rds from "aws-cdk-lib/aws-rds";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

export interface DataStackProps extends cdk.StackProps {
  readonly vpc: ec2.Vpc;
  readonly lambdaSg: ec2.SecurityGroup;
}

export class DataStack extends cdk.Stack {
  public readonly kinesisStreamPanels: kinesis.Stream;
  public readonly kinesisStreamWeather: kinesis.Stream;
  public readonly rdsCluster: rds.DatabaseCluster;
  public readonly rdsSecret: cdk.aws_secretsmanager.ISecret;
  public readonly rawBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: DataStackProps) {
    super(scope, id, props);

    cdk.Tags.of(this).add("Stack", id);
    cdk.Tags.of(this).add("Project", "SolarEdgeNL");

    // panels-stream: 2 shards — 30 panels × 1/min; 2 for redundancy
    this.kinesisStreamPanels = new kinesis.Stream(this, "PanelsStream", {
      streamName: "solar-panels-stream",
      shardCount: 2,
      retentionPeriod: cdk.Duration.hours(24),
      encryption: kinesis.StreamEncryption.MANAGED,
    });

    // weather-stream: 1 shard — 5 stations × 1 batch/10min
    this.kinesisStreamWeather = new kinesis.Stream(this, "WeatherStream", {
      streamName: "solar-weather-stream",
      shardCount: 1,
      retentionPeriod: cdk.Duration.hours(24),
      encryption: kinesis.StreamEncryption.MANAGED,
    });

    // RDS security group — ingress from lambdaSg and ecsSg (both from NetworkStack,
    // so no cross-stack cycle is introduced here).
    const dbSg = new ec2.SecurityGroup(this, "RdsSecurityGroup", {
      vpc: props.vpc,
      description: "RDS Aurora — allow Lambda and ECS on 5432",
      allowAllOutbound: false,
    });
    dbSg.addIngressRule(props.lambdaSg, ec2.Port.tcp(5432), "Lambda → RDS");
    // ECS → RDS: use VPC CIDR rather than an SG reference. ecsSg lives in
    // ComputeStack; referencing it here would create a DataStack → ComputeStack
    // cycle (ComputeStack already depends on DataStack). CIDR scope is safe
    // because RDS is in an isolated subnet reachable only from within the VPC.
    dbSg.addIngressRule(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.tcp(5432),
      "ECS tasks (VPC CIDR) → RDS"
    );

    this.rdsCluster = new rds.DatabaseCluster(this, "RdsCluster", {
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_15_4,
      }),
      serverlessV2MinCapacity: 0.5,
      serverlessV2MaxCapacity: 4,
      writer: rds.ClusterInstance.serverlessV2("writer"),
      readers: [],
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      defaultDatabaseName: "solar",
      credentials: rds.Credentials.fromGeneratedSecret("solar_admin"),
      storageEncrypted: true,
      deletionProtection: false, // dev only — set true in prod
      removalPolicy: cdk.RemovalPolicy.DESTROY, // dev — flagged
      securityGroups: [dbSg],
    });

    this.rdsSecret = this.rdsCluster.secret!;

    this.rawBucket = new s3.Bucket(this, "RawBucket", {
      bucketName: `solar-raw-archive-${this.account}-${this.region}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // dev — flagged
      autoDeleteObjects: true,
      lifecycleRules: [
        {
          id: "archive-to-glacier",
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
        },
      ],
    });

    new cdk.CfnOutput(this, "PanelsStreamName", {
      value: this.kinesisStreamPanels.streamName,
      exportName: `${this.stackName}-PanelsStreamName`,
    });
    new cdk.CfnOutput(this, "WeatherStreamName", {
      value: this.kinesisStreamWeather.streamName,
      exportName: `${this.stackName}-WeatherStreamName`,
    });
    new cdk.CfnOutput(this, "RdsClusterEndpoint", {
      value: this.rdsCluster.clusterEndpoint.hostname,
      exportName: `${this.stackName}-RdsEndpoint`,
    });
    new cdk.CfnOutput(this, "RawBucketName", {
      value: this.rawBucket.bucketName,
      exportName: `${this.stackName}-RawBucketName`,
    });
  }
}
