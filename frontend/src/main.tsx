import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App";
import RouteErrorPage from "./pages/RouteErrorPage";
import "./design-tokens.css";
import "./design-system.css";
import "./design-workspace.css";
import "./skeleton.css";
import "./print.css";

const router = createBrowserRouter([{ path: "*", element: <App />, errorElement: <RouteErrorPage /> }]);
createRoot(document.getElementById("root")!).render(<StrictMode><RouterProvider router={router} /></StrictMode>);
