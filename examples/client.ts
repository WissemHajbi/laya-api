type ChoiceQuestion = {
  type: "choice";
  instructions: string;
  criteria: Record<string, string> | string[];
};

type ScoreQuestion = {
  type: "score";
  instructions: string;
  criteria: string[];
};

type NoulQuestion = {
  type: "noul";
  instructions: string;
};

type Question = ChoiceQuestion | ScoreQuestion | NoulQuestion;

export type LayaRequest = {
  state: unknown;
  questions: Record<string, Question>;
  model?: "english" | "multilingual" | "typed-decisions";
  task?: string;
  lang?: string;
};

export async function predictWithLaya(input: LayaRequest) {
  const baseUrl = process.env.LAYA_URL ?? "http://127.0.0.1:8000";
  const response = await fetch(`${baseUrl}/predict`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
    signal: AbortSignal.timeout(30_000),
  });

  if (!response.ok) {
    throw new Error(`Laya ${response.status}: ${await response.text()}`);
  }

  return response.json();
}
