import { HashRouter, Routes, Route, Navigate } from 'react-router';
import { PageLayout } from './components/PageLayout';
import { DashboardPage } from './pages/DashboardPage';
import { PositionsPage } from './pages/PositionsPage';
import { TradeAuditPage } from './pages/TradeAuditPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';

function App() {
  return (
    <HashRouter>
      <PageLayout>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/dashboard/:portfolioId" element={<DashboardPage />} />
          <Route path="/positions" element={<PositionsPage />} />
          <Route path="/positions/:portfolioId" element={<PositionsPage />} />
          <Route path="/trades" element={<TradeAuditPage />} />
          <Route path="/trades/:portfolioId" element={<TradeAuditPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/analytics/:portfolioId" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/settings/:portfolioId" element={<SettingsPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </PageLayout>
    </HashRouter>
  );
}

export default App;
