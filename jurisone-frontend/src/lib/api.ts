const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export async function fetchUserChats(username: string) {
  const response = await fetch(`${API_BASE_URL}/chats/${username}`);
  if (!response.ok) throw new Error("Failed to fetch chats");
  return response.json();
}

export async function createNewChat(username: string) {
  const response = await fetch(`${API_BASE_URL}/chats/${username}/new`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to create chat");
  return response.json();
}

export type ApiResponse = {
  type: "research" | "draft" | "interview";
  answer: string;
  summary?: string;
  confidence?: number;
  source_type?: "rag" | "web" | "hybrid" | "unverified";
  citations?: Array<{
    source: string;
    page: number;
    snippet: string;
    source_type: string;
    url?: string | null;
  }>;
  context?: Array<{
    page_content: string;
    metadata: {
      source?: string;
      page?: number;
      url?: string | null;
      source_type?: string;
    };
  }>;
};

export async function sendMessage(
  username: string,
  chatId: string,
  message: string
): Promise<ApiResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username,
      chat_id: chatId,
      message,
    }),
  });

  if (!response.ok) throw new Error("Failed to send message");
  return response.json();
}
