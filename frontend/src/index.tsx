import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "primereact/resources/themes/md-light-indigo/theme.css";
import 'primeicons/primeicons.css';
import "./reset.css";

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
