import Navbar from "./components/navbar";
import RoleCalculator from "./components/roleCalculator";
import TeamList from "./components/teamList";
import RolesList from "./components/rolesList";
import History from "./components/history";
import { Route, Routes } from "react-router-dom";

function App() {
  return (
    <>
      <Navbar />
      <div className="container">
        <Routes>
          <Route path="/" element={<RoleCalculator />} />
          <Route path="/team" element={<TeamList />} />
          <Route path="/roles" element={<RolesList />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </div>
    </>
  );
}

export default App;
