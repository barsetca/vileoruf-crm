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

function AuthenticatedApp() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [location, setLocation] = useState(() => ({ pathname: window.location.pathname, search: window.location.search }));
  const pathname = location.pathname;

  useEffect(() => {
    if (!["/crm", "/crm/clients", "/crm/deals", "/crm/pipeline", "/crm/tasks"].includes(pathname)) {
      window.history.replaceState({}, "", "/crm");
      setLocation({ pathname: "/crm", search: "" });
    }
    const onPopState = () => setLocation({ pathname: window.location.pathname, search: window.location.search });
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  function navigate(nextPath) {
    const nextLocation = new URL(nextPath, window.location.origin);
    window.history.pushState({}, "", `${nextLocation.pathname}${nextLocation.search}`);
    setLocation({ pathname: nextLocation.pathname, search: nextLocation.search });
  }

  return <CrmShell pathname={pathname} onNavigate={navigate}>
    {pathname === "/crm" ? <DashboardPage onNavigate={navigate} /> : pathname === "/crm/deals" ? <DealsPage initialDealId={new URLSearchParams(location.search).get("deal")} /> : pathname === "/crm/pipeline" ? <PipelinePage onOpenDeal={(dealId) => navigate(`/crm/deals?deal=${dealId}`)} /> : pathname === "/crm/tasks" ? <TasksPage /> : <ClientsPage />}
    {user.role === "ADMIN" && <details className="admin-tools"><summary>{t("employees.title")}</summary><EmployeeManagement /></details>}
  </CrmShell>;
}


export default AuthenticatedApp;
