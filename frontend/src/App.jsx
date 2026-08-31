import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { AuthProvider, useAuth } from "./auth/AuthContext.jsx";
import AuthenticatedApp from "./components/AuthenticatedApp.jsx";
import AuthLoading from "./components/AuthLoading.jsx";
import LoginPage from "./components/LoginPage.jsx";


function AuthBoundary() {
  const { t, i18n } = useTranslation();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    document.documentElement.lang = i18n.resolvedLanguage ?? "ru";
    document.title = t("product.name");
  }, [i18n.resolvedLanguage, t]);

  if (isLoading) return <AuthLoading />;
  if (!isAuthenticated) return <LoginPage />;
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
