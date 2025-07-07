import { AuthMiddleware } from "../middleware/AuthMiddleware";
import { AuthPage } from "../pages/auth/AuthPage";
import { DashboardPage } from "../pages/dashboard/DashboardPage";
import { MaterialPage } from "../pages/materials/MaterialPage";
import { CMMPage } from "../pages/cmm/CMMPage";

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
      {
        path: "cmm", // ✅ YENİ - CMM route
        element: <CMMPage />,
      },
    ],
  },
  {
    path: "/auth",
    element: <AuthPage />,
  },
];
