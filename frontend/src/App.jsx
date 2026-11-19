import { Link, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/common/ProtectedRoute";
import RegisterPage from "./pages/Auth/RegisterPage";
import ProfilePage from "./pages/Profile/ProfilePage";

import "./App.css";

const PlaceholderPage = ({ title, description }) => {
  return (
    <main className="placeholder-page">
      <h1>{title}</h1>
      <p>{description}</p>
      <Link to="/">Return to CampusCart home</Link>
    </main>
  );
};

function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <PlaceholderPage
            title="Welcome to CampusCart"
            description="Your campus marketplace and student community."
          />
        }
      />

      <Route
        path="/login"
        element={
          <PlaceholderPage
            title="Login"
            description="The CampusCart login page will be built here."
          />
        }
      />

      <Route
        path="/register"
        element={<RegisterPage />}
      />

      <Route
        path="/marketplace"
        element={
          <PlaceholderPage
            title="Marketplace"
            description="Discover products listed by fellow students."
          />
        }
      />

      <Route
        path="/community"
        element={
          <PlaceholderPage
            title="Community"
            description="Connect, share and interact with other students."
          />
        }
      />

      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />

      <Route
        path="*"
        element={
          <PlaceholderPage
            title="404 - Page not found"
            description="This page does not exist."
          />
        }
      />
    </Routes>
  );
}

export default App;
