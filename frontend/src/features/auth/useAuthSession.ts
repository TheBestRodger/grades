import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { consumeMagicLink, getMe, loginWithPassword, logoutAuth } from "../../api";
import { displayRoleLabel } from "../../app/navigation";
import { queryKeys } from "../../shared/queryKeys";

const AUTH_TOKEN_STORAGE_KEY = "auth_token";

export function useAuthSession() {
  const queryClient = useQueryClient();
  const [authToken, setAuthToken] = useState<string | null>(() =>
    window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY),
  );
  const [authMessage, setAuthMessage] = useState<string | null>(null);

  const authMe = useQuery({
    queryKey: queryKeys.authMe(authToken),
    queryFn: getMe,
    enabled: Boolean(authToken),
    retry: false,
  });

  const passwordLoginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      loginWithPassword(username, password),
    onSuccess: async (session) => {
      window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, session.token);
      setAuthToken(session.token);
      setAuthMessage(`Вход выполнен: ${displayRoleLabel(session.user)} ${session.user.full_name}.`);
      await queryClient.invalidateQueries();
    },
  });

  const consumeMagicLinkMutation = useMutation({
    mutationFn: consumeMagicLink,
    onSuccess: async (session) => {
      window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, session.token);
      setAuthToken(session.token);
      setAuthMessage(`Вход выполнен: ${displayRoleLabel(session.user)} ${session.user.full_name}.`);
      window.history.replaceState({}, document.title, window.location.pathname);
      await queryClient.invalidateQueries();
    },
    onError: () => {
      window.history.replaceState({}, document.title, window.location.pathname);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: logoutAuth,
    onSuccess: async () => {
      window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
      setAuthToken(null);
      setAuthMessage("Рабочая сессия завершена, снова доступен выбор пользователя.");
      await queryClient.invalidateQueries();
    },
  });

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get(AUTH_TOKEN_STORAGE_KEY);
    if (!token || authToken || consumeMagicLinkMutation.isPending || consumeMagicLinkMutation.isSuccess) return;
    consumeMagicLinkMutation.mutate(token);
  }, [authToken, consumeMagicLinkMutation]);

  useEffect(() => {
    if (!authMe.error) return;
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    setAuthToken(null);
    setAuthMessage("Сессия истекла или была завершена. Можно войти заново.");
  }, [authMe.error]);

  return {
    authToken,
    authMessage,
    authMe,
    passwordLoginMutation,
    consumeMagicLinkMutation,
    logoutMutation,
    setAuthMessage,
  };
}
