import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext.jsx";
import ClientsPage from "./ClientsPage.jsx";
import CrmShell from "./CrmShell.jsx";
import DashboardPage from "./DashboardPage.jsx";
import DealsPage from "./DealsPage.jsx";
import EmployeeManagement from "./EmployeeManagement.jsx";
import PipelinePage from "./PipelinePage.jsx";
import TasksPage from "./TasksPage.jsx";
import BusinessSettingsPage from "./BusinessSettingsPage.jsx";
import AISettingsPage from "./AISettingsPage.jsx";
import AIHistoryPage from "./AIHistoryPage.jsx";
import IntegrationSettingsPage from "./IntegrationSettingsPage.jsx";
import InboxPage from "./InboxPage.jsx";

function AuthenticatedApp() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [location, setLocation] = useState(() => ({ pathname: window.location.pathname, search: window.location.search }));
  const pathname = location.pathname;

  useEffect(() => {
    if (!["/crm", "/crm/clients", "/crm/deals", "/crm/pipeline", "/crm/tasks", "/crm/ai-history", "/crm/inbox", "/crm/settings/business", "/crm/settings/ai", "/crm/settings/integrations"].includes(pathname) || (["/crm/settings/business", "/crm/settings/ai", "/crm/settings/integrations"].includes(pathname) && user.role !== "ADMIN")) {
      window.history.replaceState({}, "", "/crm");
      setLocation({ pathname: "/crm", search: "" });
    }
    const onPopState = () => setLocation({ pathname: window.location.pathname, search: window.location.search });
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [pathname, user.role]);

  function navigate(nextPath) {
    const nextLocation = new URL(nextPath, window.location.origin);
    window.history.pushState({}, "", `${nextLocation.pathname}${nextLocation.search}`);
    setLocation({ pathname: nextLocation.pathname, search: nextLocation.search });
  }

  return <CrmShell pathname={pathname} onNavigate={navigate}>
    {pathname === "/crm" ? <DashboardPage onNavigate={navigate} /> : pathname === "/crm/deals" ? <DealsPage initialDealId={new URLSearchParams(location.search).get("deal")} /> : pathname === "/crm/pipeline" ? <PipelinePage onOpenDeal={(dealId) => navigate(`/crm/deals?deal=${dealId}`)} /> : pathname === "/crm/tasks" ? <TasksPage /> : pathname === "/crm/ai-history" ? <AIHistoryPage /> : pathname === "/crm/inbox" ? <InboxPage /> : pathname === "/crm/settings/business" ? <BusinessSettingsPage /> : pathname === "/crm/settings/ai" ? <AISettingsPage /> : pathname === "/crm/settings/integrations" ? <IntegrationSettingsPage /> : <ClientsPage />}
    {user.role === "ADMIN" && <details className="admin-tools"><summary>{t("employees.title")}</summary><EmployeeManagement /></details>}
  </CrmShell>;
}


export default AuthenticatedApp;
