import { AuthMiddleware } from "../middleware/AuthMiddleware";
import { AuthPage } from "../pages/auth/AuthPage";
import { DashboardPage } from "../pages/dashboard/DashboardPage";

export const routes = [
  {
    element: <AuthMiddleware />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
    ],
  },
  {
    path: "/auth",
    element: <AuthPage />,
  },
];
