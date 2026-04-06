import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ecs_patterns from "aws-cdk-lib/aws-ecs-patterns";
import * as events from "aws-cdk-lib/aws-events";
import * as events_targets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as iot from "aws-cdk-lib/aws-iot";
import * as kinesis from "aws-cdk-lib/aws-kinesis";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as lambda_events from "aws-cdk-lib/aws-lambda-event-sources";
import * as path from "path";
import * as rds from "aws-cdk-lib/aws-rds";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";

export interface ComputeStackProps extends cdk.StackProps {
  readonly vpc: ec2.Vpc;
  /** Pre-created in NetworkStack to avoid a cross-stack dependency cycle. */
  readonly lambdaSg: ec2.SecurityGroup;
  readonly panelsStream: kinesis.Stream;
  readonly weatherStream: kinesis.Stream;
  readonly rdsCluster: rds.DatabaseCluster;
  readonly rdsSecret: secretsmanager.ISecret;
  readonly rawBucket: s3.Bucket;
}

export class ComputeStack extends cdk.Stack {
  public readonly apiUrl: string;

  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    cdk.Tags.of(this).add("Stack", id);
    cdk.Tags.of(this).add("Project", "SolarEdgeNL");

    // ecsSg is created here (not in NetworkStack) to prevent a
    // NetworkStack → ComputeStack DependencyCycle. ApplicationLoadBalancedFargateService
    // auto-adds its ALB SG as an ingress peer to ecsSg at synth time; if ecsSg
    // lived in NetworkStack that would create a reverse cross-stack reference.
    const ecsSg = new ec2.SecurityGroup(this, "EcsSg", {
      vpc: props.vpc,
      description: "ECS Fargate tasks",
      allowAllOutbound: true,
    });

    const knmiSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      "KnmiApiKey",
      "iot-platform/knmi-api-key"
    );

    // ── Lambda: KNMI Poller ──────────────────────────────────────────────────
    const knmiPollerFn = new lambda.Function(this, "KnmiPoller", {
      functionName: "solar-knmi-poller",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "../../services/knmi-poller/src")
      ),
      timeout: cdk.Duration.minutes(2),
      memorySize: 256,
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [props.lambdaSg],
      environment: {
        WEATHER_STREAM_NAME: props.weatherStream.streamName,
        KNMI_SECRET_ARN: knmiSecret.secretArn,
        AWS_REGION_NAME: this.region,
        POWERTOOLS_SERVICE_NAME: "knmi-poller",
      },
      tracing: lambda.Tracing.ACTIVE,
    });

    props.weatherStream.grantWrite(knmiPollerFn);
    knmiSecret.grantRead(knmiPollerFn);

    new events.Rule(this, "KnmiSchedule", {
      schedule: events.Schedule.rate(cdk.Duration.minutes(10)),
      targets: [new events_targets.LambdaFunction(knmiPollerFn)],
    });

    // ── Lambda: Panel Processor (Kinesis consumer, STREAM_TYPE=panels) ───────
    const panelProcessorFn = new lambda.Function(this, "PanelProcessor", {
      functionName: "solar-panel-processor",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "../../services/panel-processor/src")
      ),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [props.lambdaSg],
      environment: {
        RAW_BUCKET_NAME: props.rawBucket.bucketName,
        DB_SECRET_ARN: props.rdsSecret.secretArn,
        STREAM_TYPE: "panels",
        AWS_REGION_NAME: this.region,
        POWERTOOLS_SERVICE_NAME: "panel-processor",
      },
      tracing: lambda.Tracing.ACTIVE,
    });

    panelProcessorFn.addEventSource(
      new lambda_events.KinesisEventSource(props.panelsStream, {
        startingPosition: lambda.StartingPosition.LATEST,
        batchSize: 100,
        bisectBatchOnError: true,
      })
    );

    // ── Lambda: Weather Processor (Kinesis consumer, STREAM_TYPE=weather) ────
    const weatherProcessorFn = new lambda.Function(this, "WeatherProcessor", {
      functionName: "solar-weather-processor",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "../../services/panel-processor/src")
      ),
      timeout: cdk.Duration.minutes(5),
      memorySize: 256,
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [props.lambdaSg],
      environment: {
        RAW_BUCKET_NAME: props.rawBucket.bucketName,
        DB_SECRET_ARN: props.rdsSecret.secretArn,
        STREAM_TYPE: "weather",
        AWS_REGION_NAME: this.region,
        POWERTOOLS_SERVICE_NAME: "weather-processor",
      },
      tracing: lambda.Tracing.ACTIVE,
    });

    weatherProcessorFn.addEventSource(
      new lambda_events.KinesisEventSource(props.weatherStream, {
        startingPosition: lambda.StartingPosition.LATEST,
        batchSize: 100,
        bisectBatchOnError: true,
      })
    );

    for (const fn of [panelProcessorFn, weatherProcessorFn]) {
      props.rdsSecret.grantRead(fn);
      fn.addToRolePolicy(
        new iam.PolicyStatement({
          actions: ["s3:PutObject"],
          resources: [`${props.rawBucket.bucketArn}/raw/*`],
        })
      );
    }

    // ── IoT Core Rule → panels-stream ────────────────────────────────────────
    const iotRole = new iam.Role(this, "IotKinesisRole", {
      assumedBy: new iam.ServicePrincipal("iot.amazonaws.com"),
    });
    props.panelsStream.grantWrite(iotRole);

    new iot.CfnTopicRule(this, "PanelTelemetryRule", {
      ruleName: "SolarPanelTelemetryToKinesis",
      topicRulePayload: {
        sql: "SELECT * FROM 'panels/+/telemetry'",
        actions: [
          {
            kinesis: {
              streamName: props.panelsStream.streamName,
              roleArn: iotRole.roleArn,
              partitionKey: "${panel_id}",
            },
          },
        ],
        ruleDisabled: false,
        awsIotSqlVersion: "2016-03-23",
      },
    });

    // ── ECS Fargate: FastAPI ─────────────────────────────────────────────────
    const cluster = new ecs.Cluster(this, "Cluster", {
      vpc: props.vpc,
      containerInsightsV2: ecs.ContainerInsights.ENABLED,
    });

    const fargateService =
      new ecs_patterns.ApplicationLoadBalancedFargateService(
        this,
        "FastApiService",
        {
          cluster,
          cpu: 256,
          memoryLimitMiB: 512,
          desiredCount: 1,
          taskSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
          securityGroups: [ecsSg],
          taskImageOptions: {
            image: ecs.ContainerImage.fromAsset(
              path.join(__dirname, "../../services/api")
            ),
            containerPort: 8000,
            environment: {
              AWS_REGION_NAME: this.region,
              POWERTOOLS_SERVICE_NAME: "solar-api",
            },
            secrets: {
              DB_SECRET_ARN: ecs.Secret.fromSecretsManager(props.rdsSecret),
            },
          },
          healthCheckGracePeriod: cdk.Duration.seconds(30),
        }
      );

    // Allow the ALB to reach the container port on the ECS SG.
    // Using a CIDR-based rule (VPC CIDR) rather than an SG reference to avoid
    // a cross-stack cycle between NetworkStack endpoints and this stack's ALB SG.
    fargateService.service.connections.allowFrom(
      ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.tcp(8000),
      "ALB → ECS on 8000 (via VPC CIDR)"
    );

    props.rdsSecret.grantRead(fargateService.taskDefinition.taskRole);

    this.apiUrl = `http://${fargateService.loadBalancer.loadBalancerDnsName}`;

    new cdk.CfnOutput(this, "ApiUrl", {
      value: this.apiUrl,
      exportName: `${this.stackName}-ApiUrl`,
    });
    new cdk.CfnOutput(this, "AlbDnsName", {
      value: fargateService.loadBalancer.loadBalancerDnsName,
      exportName: `${this.stackName}-AlbDnsName`,
    });
  }
}
