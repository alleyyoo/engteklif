import { Navigate, Outlet } from "react-router-dom";
import { DefaultLayout } from "../components/Layout/DefaultLayout";
import { verifyToken } from "../utils/jwt";

export const AuthMiddleware = (props: any) => {
  const token = localStorage.getItem("accessToken");
  const isAuthenticated = verifyToken(token || "");
  console.log(isAuthenticated);

  return isAuthenticated ? (
    <DefaultLayout>
      <Outlet />
    </DefaultLayout>
  ) : (
    <Navigate to="/auth" />
  );
};
