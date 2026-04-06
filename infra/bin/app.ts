#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { NetworkStack } from "../lib/network-stack";
import { DataStack } from "../lib/data-stack";
import { ComputeStack } from "../lib/compute-stack";
import { FrontendStack } from "../lib/frontend-stack";
import { ObservabilityStack } from "../lib/observability-stack";

const app = new cdk.App();

const env: cdk.Environment = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? "eu-west-1",
};

// Stack dependency order:
//   Network → Data → Compute → Frontend + Observability
//
// Security groups are created in NetworkStack so DataStack can add RDS
// ingress rules without creating a cycle with ComputeStack.

const network = new NetworkStack(app, "IoT-NetworkStack", { env });

const data = new DataStack(app, "IoT-DataStack", {
  env,
  vpc: network.vpc,
  lambdaSg: network.lambdaSg,
});

const compute = new ComputeStack(app, "IoT-ComputeStack", {
  env,
  vpc: network.vpc,
  lambdaSg: network.lambdaSg,
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
