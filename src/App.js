import Navbar from "./components/navbar";
import { Route, Routes } from "react-router-dom";
import { menuItems } from "./components/data/menuItems";

import "primereact/resources/themes/lara-dark-teal/theme.css"; //theme
import "primereact/resources/primereact.min.css"; //core css
import "primeicons/primeicons.css"; //icons

function App() {
  return (
    <div className="container min-h-screen min-w-full p-4">
      <Navbar />
      <main>
        <Routes>
          {menuItems.map((item, index) => {
            return (
              <Route key={index} path={item.url} element={item.component} />
            );
          })}
        </Routes>
      </main>
    </div>
  );
}

export default App;
