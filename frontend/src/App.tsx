import { PrimeReactProvider } from 'primereact/api';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { routes } from './utils/router';

const router = createBrowserRouter(routes);

export const App = () => {
  return (
    <PrimeReactProvider>
      <RouterProvider router={router} />
    </PrimeReactProvider>
  );
};
