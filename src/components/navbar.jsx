import { NavLink } from "react-router-dom";

function Navbar() {
  return (
    <nav>
      <ul className="flex place-content-center gap-6 text-2xl">
        <li>
          <NavLink to="/">Home</NavLink>
        </li>
        <li>
          <NavLink to="/team">Team</NavLink>
        </li>
        <li>
          <NavLink to="/roles">Roles</NavLink>
        </li>
        <li>
          <NavLink to="/history">History</NavLink>
        </li>
      </ul>
    </nav>
  );
}

export default Navbar;
