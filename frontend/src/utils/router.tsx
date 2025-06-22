import { AuthMiddleware } from "../middleware/AuthMiddleware";
import { AuthPage } from "../pages/auth/AuthPage";
import { DashboardPage } from "../pages/dashboard/DashboardPage";
import { MaterialPage } from "../pages/materials/MaterialPage";

export const routes = [
  {
    element: <AuthMiddleware />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: "materials",
        element: <MaterialPage />,
      },
    ],
  },
  {
    path: "/auth",
    element: <AuthPage />,
  },
];
