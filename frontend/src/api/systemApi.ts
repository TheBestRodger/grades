import { request } from "./request";
import { API_URL } from "./urls";
import type { Health } from "./types";

export const getHealth = () => request<Health>(API_URL.system.health);
