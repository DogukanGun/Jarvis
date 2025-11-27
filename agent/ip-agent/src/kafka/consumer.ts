import { Kafka, Consumer, EachMessagePayload } from 'kafkajs';
import { ipRegistrationService } from '../services/ipRegistration';
import { Address } from 'viem';

export interface IPRegistrationMessage {
  id: string;
  user_id: string;
  asset_id: string;
  owner_address: string;
  title: string;
  description: string;
  image_data: string; // base64
  commercial_use?: boolean;
  commercial_rev_share?: number;
  minting_fee?: string;
  timestamp: number;
}

export class IPAgentConsumer {
  private kafka: Kafka;
  private consumer: Consumer;

  constructor() {
    const brokers = (process.env.KAFKA_BROKERS || 'localhost:9092').split(',');

    this.kafka = new Kafka({
      clientId: 'ip-agent',
      brokers: brokers,
    });

    this.consumer = this.kafka.consumer({
      groupId: 'ip-agent-group',
    });
  }

  async connect() {
    await this.consumer.connect();
    console.log('Kafka consumer connected');

    await this.consumer.subscribe({
      topic: 'ip-registration-requests',
      fromBeginning: false,
    });

    console.log('Subscribed to topic: ip-registration-requests');
  }

  async start() {
    await this.consumer.run({
      eachMessage: async (payload: EachMessagePayload) => {
        await this.handleMessage(payload);
      },
    });
  }

  private async handleMessage(payload: EachMessagePayload) {
    const { message } = payload;

    try {
      const messageValue = message.value?.toString();
      if (!messageValue) {
        console.log('Empty message received');
        return;
      }

      console.log(`Received message: ${message.key?.toString()}`);

      const data: IPRegistrationMessage = JSON.parse(messageValue);

      console.log(`Processing IP registration request for asset: ${data.asset_id}`);
      console.log(`Owner: ${data.owner_address}, Title: ${data.title}`);

      // Register IP on Story Protocol
      const result = await ipRegistrationService.registerIP({
        title: data.title,
        description: data.description,
        imageData: data.image_data,
        ownerAddress: data.owner_address as Address,
        creatorName: data.user_id,
        commercialUse: data.commercial_use || false,
        commercialRevShare: data.commercial_rev_share || 5,
        mintingFee: data.minting_fee || '0.1',
      });

      if (result.success) {
        console.log(`✓ IP registered successfully!`);
        console.log(`  IP ID: ${result.ipId}`);
        console.log(`  TX Hash: ${result.txHash}`);
        console.log(`  Explorer: ${result.explorerUrl}`);

        // TODO: Send success response back via Kafka or store in database
        // For now, just log
      } else {
        console.error(`✗ Failed to register IP: ${result.error}`);
        // TODO: Send failure response back
      }
    } catch (error: any) {
      console.error('Error processing message:', error);
    }
  }

  async disconnect() {
    await this.consumer.disconnect();
    console.log('Kafka consumer disconnected');
  }
}

