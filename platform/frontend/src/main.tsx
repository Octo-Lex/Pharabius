import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import App from "./App";
import Layout from "./components/Layout";
import RepositoryList from "./views/RepositoryList";
import RepositoryDashboard from "./views/RepositoryDashboard";
import FindingsTable from "./views/FindingsTable";
import PortfolioSummary from "./views/PortfolioSummary";
import UploadPage from "./views/UploadPage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<RepositoryList />} />
          <Route path="/repositories/:repoId" element={<RepositoryDashboard />} />
          <Route path="/repositories/:repoId/findings" element={<FindingsTable />} />
          <Route path="/portfolio" element={<PortfolioSummary />} />
          <Route path="/upload" element={<UploadPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
