import { Dashboard } from './components/Dashboard';
import { StatusPage } from './components/StatusPage';

function App() {
  if (window.location.pathname === '/status') {
    return <StatusPage />;
  }
  return <Dashboard />;
}

export default App;
