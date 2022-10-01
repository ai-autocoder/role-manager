import Navbar from "./components/navbar";
// import RoleCalculator from "./components/roleCalculator";
// import TeamList from "./components/teamList";
// import RolesList from "./components/rolesList";
// import History from "./components/history";
import { Route, Routes } from "react-router-dom";
import { MenuItems } from "./components/menuItems";

function App() {
  return (
    <>
      <Navbar />
      <div className="container">
        <Routes>
          {MenuItems.map((item, index) => {
            return (
              <Route key={index} path={item.url} element={item.component} />
            );
          })}
        </Routes>
      </div>
    </>
  );
}

export default App;
