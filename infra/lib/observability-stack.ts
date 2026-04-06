import * as cdk from "aws-cdk-lib";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatch_actions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as kinesis from "aws-cdk-lib/aws-kinesis";
import * as sns from "aws-cdk-lib/aws-sns";
import * as xray from "aws-cdk-lib/aws-xray";
import { Construct } from "constructs";

export interface ObservabilityStackProps extends cdk.StackProps {
  readonly panelsStream: kinesis.Stream;
  readonly weatherStream: kinesis.Stream;
  readonly panelProcessorFunctionName: string;
  readonly weatherProcessorFunctionName: string;
  readonly knmiPollerFunctionName: string;
}

export class ObservabilityStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ObservabilityStackProps) {
    super(scope, id, props);

    cdk.Tags.of(this).add("Stack", id);
    cdk.Tags.of(this).add("Project", "SolarEdgeNL");

    // ── SNS Topic ────────────────────────────────────────────────────────────
    const alertTopic = new sns.Topic(this, "AlertTopic", {
      topicName: "solar-platform-alerts",
      displayName: "SolarEdge NL Platform Alerts",
    });

    // ── Kinesis Metrics ──────────────────────────────────────────────────────
    const panelsIteratorAge = new cloudwatch.Metric({
      namespace: "AWS/Kinesis",
      metricName: "GetRecords.IteratorAgeMilliseconds",
      dimensionsMap: { StreamName: props.panelsStream.streamName },
      statistic: "Maximum",
      period: cdk.Duration.minutes(1),
    });

    const weatherIteratorAge = new cloudwatch.Metric({
      namespace: "AWS/Kinesis",
      metricName: "GetRecords.IteratorAgeMilliseconds",
      dimensionsMap: { StreamName: props.weatherStream.streamName },
      statistic: "Maximum",
      period: cdk.Duration.minutes(1),
    });

    // ── Lambda Error Metrics ─────────────────────────────────────────────────
    const lambdaErrorMetric = (fnName: string): cloudwatch.Metric =>
      new cloudwatch.Metric({
        namespace: "AWS/Lambda",
        metricName: "Errors",
        dimensionsMap: { FunctionName: fnName },
        statistic: "Sum",
        period: cdk.Duration.minutes(5),
      });

    // ── Alarms ───────────────────────────────────────────────────────────────
    const alarms: cloudwatch.Alarm[] = [
      new cloudwatch.Alarm(this, "PanelsIteratorAgeAlarm", {
        alarmName: "solar-panels-stream-iterator-age",
        alarmDescription: "Panels stream iterator age > 60s — processor lag",
        metric: panelsIteratorAge,
        threshold: 60_000, // milliseconds
        evaluationPeriods: 2,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }),

      new cloudwatch.Alarm(this, "WeatherIteratorAgeAlarm", {
        alarmName: "solar-weather-stream-iterator-age",
        alarmDescription: "Weather stream iterator age > 60s — processor lag",
        metric: weatherIteratorAge,
        threshold: 60_000,
        evaluationPeriods: 2,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }),

      new cloudwatch.Alarm(this, "PanelProcessorErrorAlarm", {
        alarmName: "solar-panel-processor-errors",
        metric: lambdaErrorMetric(props.panelProcessorFunctionName),
        threshold: 1,
        evaluationPeriods: 1,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }),

      new cloudwatch.Alarm(this, "KnmiPollerErrorAlarm", {
        alarmName: "solar-knmi-poller-errors",
        metric: lambdaErrorMetric(props.knmiPollerFunctionName),
        threshold: 1,
        evaluationPeriods: 1,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      }),
    ];

    // Wire alarms → SNS
    for (const alarm of alarms) {
      alarm.addAlarmAction(new cloudwatch_actions.SnsAction(alertTopic));
    }

    // ── CloudWatch Dashboard ─────────────────────────────────────────────────
    new cloudwatch.Dashboard(this, "Dashboard", {
      dashboardName: "SolarEdgeNL-Platform",
      widgets: [
        [
          new cloudwatch.GraphWidget({
            title: "Kinesis Iterator Age (ms)",
            left: [panelsIteratorAge, weatherIteratorAge],
            width: 12,
          }),
          new cloudwatch.GraphWidget({
            title: "Lambda Errors",
            left: [
              lambdaErrorMetric(props.panelProcessorFunctionName),
              lambdaErrorMetric(props.weatherProcessorFunctionName),
              lambdaErrorMetric(props.knmiPollerFunctionName),
            ],
            width: 12,
          }),
        ],
      ],
    });

    // ── X-Ray Group ──────────────────────────────────────────────────────────
    new xray.CfnGroup(this, "XRayGroup", {
      groupName: "solar-platform",
      filterExpression: 'annotation.Project = "SolarEdgeNL"',
      insightsConfiguration: {
        insightsEnabled: true,
        notificationsEnabled: false,
      },
    });
  }
}
