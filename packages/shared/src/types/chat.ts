/** Role of a participant in a chat conversation. */
export type MessageRole = 'user' | 'assistant' | 'system';

/** A single message in a conversation thread. */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string; // ISO 8601
  /** Optional structured data extracted by the AI (e.g. event draft). */
  metadata?: Record<string, unknown>;
}

/** A conversation session between user and the LanDo agent. */
export interface Conversation {
  id: string;
  title?: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

/** Request payload to send a message to the AI agent. */
export interface SendMessageRequest {
  conversationId?: string; // creates new conversation if omitted
  content: string;
}
