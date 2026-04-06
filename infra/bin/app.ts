#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { NetworkStack } from "../lib/network-stack";
import { DataStack } from "../lib/data-stack";
import { ComputeStack } from "../lib/compute-stack";
import { FrontendStack } from "../lib/frontend-stack";
import { ObservabilityStack } from "../lib/observability-stack";

const app = new cdk.App();

// ❌ Never hardcode account IDs or region strings here — use environment variables
const env: cdk.Environment = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? "eu-west-1",
};

// Stack dependency order: Network → Data → Compute → Frontend + Observability
// Rule: stacks only receive what they need — never the whole stack as a prop

const network = new NetworkStack(app, "IoT-NetworkStack", { env });

const data = new DataStack(app, "IoT-DataStack", {
  env,
  vpc: network.vpc,
});

const compute = new ComputeStack(app, "IoT-ComputeStack", {
  env,
  vpc: network.vpc,
  panelsStream: data.kinesisStreamPanels,
  weatherStream: data.kinesisStreamWeather,
  rdsCluster: data.rdsCluster,
  rdsSecret: data.rdsSecret,
  rawBucket: data.rawBucket,
});

new FrontendStack(app, "IoT-FrontendStack", {
  env,
  apiUrl: compute.apiUrl,
});

new ObservabilityStack(app, "IoT-ObservabilityStack", {
  env,
  panelsStream: data.kinesisStreamPanels,
  weatherStream: data.kinesisStreamWeather,
  panelProcessorFunctionName: "solar-panel-processor",
  weatherProcessorFunctionName: "solar-weather-processor",
  knmiPollerFunctionName: "solar-knmi-poller",
});

app.synth();
