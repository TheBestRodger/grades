import { AppShell } from "./AppShell";
import { AppModals } from "./AppModals";
import { AppPages } from "./AppPages";
import { useAppControllerContext } from "./useAppControllerContext";
import { SessionLoadingPage } from "../components/SessionLoadingPage";
import { LoginPage } from "../pages/LoginPage";

export function AppController() {
  const app = useAppControllerContext();

  if (!app.authToken && !app.activeUser) {
    return (
      <LoginPage
        authError={app.authError}
        authMessage={app.authMessage}
        isRequesting={app.isLoginRequesting}
        onLogin={app.login}
      />
    );
  }

  if (app.authToken && !app.activeUser) {
    return <SessionLoadingPage />;
  }

  return (
    <AppShell {...app.shell}>
      <AppPages context={app.controllerContext} />
      <AppModals context={app.controllerContext} />
    </AppShell>
  );
}
