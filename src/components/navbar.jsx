import { NavLink, useLocation } from "react-router-dom";
import { menuItems } from "./data/menuItems";

function Navbar() {
  const location = useLocation();

  return (
    <nav className="p-4 mb-8">
      <ul className="flex place-content-center gap-6 text-2xl font-medium">
        {menuItems.map((item, index) => {
          return (
            <li key={index}>
              <NavLink
                to={item.url}
                className={`
                px-6
                py-2.5
                opacity-70 
                rounded
                transition
                duration-150
                ease-in-out
                flex
                items-center
                whitespace-nowrap
                hover:opacity-100
                dark: opacity-100
                dark: hover:bg-slate-500
                ${
                  location.pathname === item.url
                    ? `
                  dark: bg-green-600
                  dark: hover:bg-green-600`
                    : ""
                }
                `}
                end
              >
                {item.Title}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export default Navbar;
