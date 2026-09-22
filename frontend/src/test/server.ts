import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
export { API_URL, fixtureStatsSummary, fixtureUser, fixtureUserWord, fixtureWord } from "./handlers";
