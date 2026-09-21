export interface Topic {
  slug: string;
  name_ru: string;
}

export interface TopicWithCount extends Topic {
  word_count: number;
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
}

export interface Word {
  id: string;
  text: string;
  translation: string;
  transcription: string | null;
  part_of_speech: string | null;
  examples: string[];
  cefr_level: string | null;
  topic: Topic | null;
}

export interface FSRSState {
  state: "new" | "learning" | "review" | "relearning";
  due_date: string;
  reps: number;
  lapses: number;
}

export interface UserWord {
  user_word_id: string;
  word: Word;
  fsrs_state: FSRSState;
}

export interface WordListResponse {
  items: Word[];
  total: number;
  page: number;
}

export type ActivityType = "flip" | "multiple_choice" | "recall";

export const RATING = { AGAIN: 1, HARD: 2, GOOD: 3, EASY: 4 } as const;
