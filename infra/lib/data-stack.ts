import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as kinesis from "aws-cdk-lib/aws-kinesis";
import * as rds from "aws-cdk-lib/aws-rds";
import * as s3 from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";

export interface DataStackProps extends cdk.StackProps {
  readonly vpc: ec2.Vpc;
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

    // ── Kinesis Streams ──────────────────────────────────────────────────────
    // panels-stream: 2 shards — 30 panels × 1/min trivial; 2 for redundancy
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

    // ── RDS Aurora PostgreSQL Serverless v2 ──────────────────────────────────
    // Isolated subnet — no internet route; SG will be locked to ECS SG on 5432
    const dbSecurityGroup = new ec2.SecurityGroup(this, "RdsSecurityGroup", {
      vpc: props.vpc,
      description: "Allow ECS tasks to connect to RDS on port 5432",
      allowAllOutbound: false,
    });

    this.rdsCluster = new rds.DatabaseCluster(this, "RdsCluster", {
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_15_4,
      }),
      serverlessV2MinCapacity: 0.5, // scales to zero when idle
      serverlessV2MaxCapacity: 4, // caps cost in dev
      writer: rds.ClusterInstance.serverlessV2("writer"),
      readers: [], // no reader in dev
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      defaultDatabaseName: "solar",
      credentials: rds.Credentials.fromGeneratedSecret("solar_admin"),
      storageEncrypted: true,
      deletionProtection: false, // dev only — set true in prod
      removalPolicy: cdk.RemovalPolicy.DESTROY, // dev — flagged
      securityGroups: [dbSecurityGroup],
    });

    this.rdsSecret = this.rdsCluster.secret!;

    // ── S3 Raw Archive Bucket ────────────────────────────────────────────────
    this.rawBucket = new s3.Bucket(this, "RawBucket", {
      bucketName: `solar-raw-archive-${this.account}-${this.region}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL, // security: no public access
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // dev — flagged
      autoDeleteObjects: true, // dev only
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

    // ── Outputs ──────────────────────────────────────────────────────────────
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
