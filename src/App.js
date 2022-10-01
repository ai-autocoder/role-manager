import Navbar from "./components/navbar";
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
