import Navbar from "./components/navbar";
import { Route, Routes } from "react-router-dom";
import { menuItems } from "./components/data/menuItems";

function App() {
  return (
    <div className="container min-h-screen min-w-full dark:bg-neutral-700 text-neutral-200 p-4">
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
