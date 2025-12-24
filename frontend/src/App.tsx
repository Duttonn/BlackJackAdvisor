import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GameProvider } from './context/GameContext';
import { Layout } from './components/Layout';
import { Home } from './pages/Home';
import { Training } from './pages/Training';
import { Shadowing } from './pages/Shadowing';

function App() {
  return (
    <GameProvider>
      <Router>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/training" element={<Training />} />
            <Route path="/shadowing" element={<Shadowing />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Router>
    </GameProvider>
  );
}

export default App;
