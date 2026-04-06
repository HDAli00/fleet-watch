import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";

export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  /** Security group for all Lambda functions — RDS ingress added in DataStack. */
  public readonly lambdaSg: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props: cdk.StackProps) {
    super(scope, id, props);

    cdk.Tags.of(this).add("Stack", id);
    cdk.Tags.of(this).add("Project", "SolarEdgeNL");

    this.vpc = new ec2.Vpc(this, "Vpc", {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        { name: "public", subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: "private", subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
        { name: "isolated", subnetType: ec2.SubnetType.PRIVATE_ISOLATED, cidrMask: 24 },
      ],
    });

    // S3 Gateway endpoint — free, no SG required (route-table-based), no cycle risk.
    this.vpc.addGatewayEndpoint("S3Endpoint", {
      service: ec2.GatewayVpcEndpointAwsService.S3,
    });

    // Note: Kinesis and Secrets Manager interface endpoints are intentionally
    // omitted. Interface endpoints require security groups; CDK auto-tracks
    // connections from each consumer SG, creating cross-stack dependency cycles
    // in a multi-stack setup. NAT Gateway handles that traffic in dev.

    // lambdaSg is created here (before DataStack) so DataStack can add RDS
    // ingress rules without creating a cycle with ComputeStack.
    // ecsSg is intentionally created in ComputeStack — ALB auto-adds its SG as
    // an ingress peer to ecsSg at synthesis time; keeping ecsSg in NetworkStack
    // would create a NetworkStack → ComputeStack reference (DependencyCycle).
    this.lambdaSg = new ec2.SecurityGroup(this, "LambdaSg", {
      vpc: this.vpc,
      description: "Lambda functions",
      allowAllOutbound: true,
    });

    new cdk.CfnOutput(this, "VpcId", {
      value: this.vpc.vpcId,
      exportName: `${this.stackName}-VpcId`,
    });
  }
}
