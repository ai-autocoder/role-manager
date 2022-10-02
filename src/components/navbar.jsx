import { NavLink } from "react-router-dom";
import { MenuItems } from "./menuItems";

function Navbar() {
  return (
    <nav className="p-4">
      <ul className="flex place-content-center gap-6 text-2xl font-medium">
        {MenuItems.map((item, index) => {
          return (
            <li key={index}>
              <NavLink
                to={item.url}
                className="opacity-70 hover:opacity-100"
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
