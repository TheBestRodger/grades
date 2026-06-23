import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { downloadHrExport, downloadProfileTemplateExport } from "../api";
import { useAnalytics } from "../features/analytics";
import { useAuthSession } from "../features/auth";
import { useCampaigns, useCampaignWorkflow } from "../features/campaigns";
import { useDocumentWorkflow, useDocuments } from "../features/documents";
import { useMyProfiles, useProfileWorkflow } from "../features/profile";
import { useHrReviews, useManagerReviews, useReviewWorkflow } from "../features/reviews";
import { useSettings, useSettingsWorkflow } from "../features/settings";
import { useStructureData, useStructureWorkflow } from "../features/structure";
import { useNotifications } from "../features/notifications";
import { navForRole, type DataScope, type SectionId } from "./navigation";

export function useAppControllerContext() {
  const queryClient = useQueryClient();
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [activeSection, setActiveSection] = useState<SectionId>("structure");
  const [operationMessage, setOperationMessage] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const dataScope = useMemo<DataScope>(() => "work", []);

  const {
    authToken,
    authMessage,
    setAuthMessage,
    authMe,
    passwordLoginMutation,
    consumeMagicLinkMutation,
    logoutMutation,
  } = useAuthSession();

  useEffect(() => {
    setSelectedUserId(authMe.data?.id ?? null);
  }, [authMe.data]);

  const selectedUser = authMe.data;
  const activeUser = authMe.data;
  const isHr = Boolean(activeUser?.is_hr || activeUser?.role === "hr");
  const isManager = activeUser?.role === "manager";
  const navItems = useMemo(() => navForRole(activeUser?.role, isHr), [activeUser?.role, isHr]);

  useEffect(() => {
    const activeItem = navItems.find((item) => item.id === activeSection && !item.disabled);
    if (!activeItem) {
      setActiveSection(navItems.find((item) => !item.disabled)?.id ?? "profile");
    }
  }, [activeSection, navItems]);

  const { health, personalProfiles } = useMyProfiles(selectedUserId);
  const { summary, tree, workTree, workSummary, managers, workManagers } = useStructureData(
    selectedUserId,
    isHr,
    dataScope,
  );
  const { campaigns, audit } = useCampaigns(selectedUserId, dataScope, isHr);
  const { hrAnalytics } = useAnalytics(selectedUserId, dataScope, isHr);
  const { aiSettings, questionnaireSettings } = useSettings(selectedUserId, isHr);
  const { hrReviews } = useHrReviews(selectedUserId, dataScope, isHr);
  const { documents, managerDocuments } = useDocuments(selectedUserId, dataScope, isHr, isManager);
  const { managerReviews, managerOverview } = useManagerReviews(selectedUserId, isManager);
  const {
    notifications,
    notificationUnreadCount,
    markNotificationReadMutation,
    markAllNotificationsReadMutation,
  } = useNotifications(selectedUserId);

  const campaignWorkflow = useCampaignWorkflow({
    campaignsData: campaigns.data,
    dataScope,
    queryClient,
    selectedUserId,
    setExportError,
    setOperationMessage,
  });

  const structureWorkflow = useStructureWorkflow({
    authMe,
    dataScope,
    queryClient,
    selectedUserId,
    setCredentialsFileBlob: campaignWorkflow.setCredentialsFileBlob,
    setOperationMessage,
    setSelectedUserId,
  });

  const documentWorkflow = useDocumentWorkflow({ queryClient, selectedUserId, setOperationMessage });
  const profileWorkflow = useProfileWorkflow({ dataScope, queryClient, selectedUserId });
  const reviewWorkflow = useReviewWorkflow({ dataScope, queryClient, selectedUserId });
  const settingsWorkflow = useSettingsWorkflow({ queryClient, selectedUserId, setOperationMessage });

  async function exportHrData(kind: "profiles" | "campaigns", format: "csv" | "json") {
    if (!selectedUserId) return;
    setExportError(null);
    try {
      await downloadHrExport(selectedUserId, kind, format);
      setOperationMessage(
        `Выгрузка ${kind === "profiles" ? "профилей" : "кампаний"} ${format.toUpperCase()} подготовлена.`,
      );
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Не удалось подготовить выгрузку.");
    }
  }

  async function exportPersonalProfile(profileId: number) {
    if (!selectedUserId) return;
    await downloadProfileTemplateExport(selectedUserId, profileId);
  }

  const activePersonalProfile = personalProfiles.data?.[0] ?? null;
  const authError =
    passwordLoginMutation.error?.message ??
    consumeMagicLinkMutation.error?.message ??
    logoutMutation.error?.message ??
    null;

  const controllerContext = {
    ...campaignWorkflow,
    ...documentWorkflow,
    ...profileWorkflow,
    ...reviewWorkflow,
    ...settingsWorkflow,
    ...structureWorkflow,
    activePersonalProfile,
    activeSection,
    activeUser,
    aiSettings,
    audit,
    campaigns,
    dataScope,
    documents,
    exportError,
    exportHrData,
    exportPersonalProfile,
    health,
    hrAnalytics,
    hrReviews,
    isHr,
    isManager,
    managerDocuments,
    managerOverview,
    managerReviews,
    managers,
    operationMessage,
    questionnaireSettings,
    selectedUser,
    summary,
    tree,
    workManagers,
    workSummary,
    workTree,
  };

  return {
    activeUser,
    authError,
    authMessage,
    authToken,
    controllerContext,
    isLoginRequesting: passwordLoginMutation.isPending || consumeMagicLinkMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
    login: (username: string, password: string) => {
      setAuthMessage(null);
      passwordLoginMutation.mutate({ username, password });
    },
    logout: () => logoutMutation.mutate(),
    navItems,
    onSectionChange: setActiveSection,
    shell: {
      activeSection,
      activeUser: authMe.data,
      authError,
      authMessage,
      dataScope,
      isMarkingAllNotificationsRead: markAllNotificationsReadMutation.isPending,
      isNotificationsLoading: notifications.isLoading,
      isLoggingOut: logoutMutation.isPending,
      navItems,
      notifications: notifications.data?.items ?? [],
      notificationUnreadCount:
        notificationUnreadCount.data?.unread_count ??
        notifications.data?.unread_count ??
        0,
      onLogout: () => logoutMutation.mutate(),
      onMarkAllNotificationsRead: () => markAllNotificationsReadMutation.mutate(),
      onMarkNotificationRead: (notificationId: number) =>
        markNotificationReadMutation.mutate(notificationId),
      onNotificationNavigate: (section: SectionId) => setActiveSection(section),
      onSectionChange: setActiveSection,
    },
  };
}
