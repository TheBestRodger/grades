import { request } from "./request";
import { API_URL } from "./urls";
import type { AuthSession, AuthUser, MagicLinkResponse } from "./types";

export const getMe = () => request<AuthUser>(API_URL.auth.me);

export const loginWithPassword = (username: string, password: string) =>
  request<AuthSession>(API_URL.auth.login, {
    method: "POST",
    body: { username, password },
  });

export const requestMagicLink = (email: string) =>
  request<MagicLinkResponse>(API_URL.auth.requestMagicLink, {
    method: "POST",
    body: { email },
  });

export const consumeMagicLink = (token: string) =>
  request<AuthSession>(API_URL.auth.consumeMagicLink, {
    method: "POST",
    body: { token },
  });

export const logoutAuth = () =>
  request<{ revoked: boolean }>(API_URL.auth.logout, {
    method: "POST",
  });
