import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthProvider, useAuth } from "./auth/AuthContext.jsx";
import AuthenticatedApp from "./components/AuthenticatedApp.jsx";
import AuthLoading from "./components/AuthLoading.jsx";
import LoginPage from "./components/LoginPage.jsx";
import PublicPage from "./components/PublicPage.jsx";


function AuthBoundary() {
  const { t, i18n } = useTranslation();
  const { isAuthenticated, isLoading } = useAuth();
  const [pathname, setPathname] = useState(window.location.pathname);

  function navigate(path) { window.history.pushState({}, "", path); setPathname(path); }

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!isLoading && !isAuthenticated && pathname.startsWith("/crm")) {
      window.history.replaceState({}, "", "/login");
      setPathname("/login");
    }
  }, [isAuthenticated, isLoading, pathname]);

  useEffect(() => {
    document.documentElement.lang = i18n.resolvedLanguage ?? "ru";
    document.title = t("product.name");
  }, [i18n.resolvedLanguage, t]);

  if (isLoading && pathname !== "/") return <AuthLoading />;
  if (pathname === "/" && !isAuthenticated) return <PublicPage onLogin={() => navigate("/login")} />;
  if (!isAuthenticated) return <LoginPage onHome={() => navigate("/")} />;
  return <AuthenticatedApp />;
}


function App() {
  return (
    <AuthProvider>
      <AuthBoundary />
    </AuthProvider>
  );
}


export default App;
