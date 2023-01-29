import { NavLink, useLocation } from "react-router-dom";

function Navbar() {
  const location = useLocation();

  const menuItems = [
    {
      title: "Home",
      url: "/",
    },
    {
      title: "Team",
      url: "/team",
    },
    {
      title: "Roles",
      url: "/roles",
    },
    {
      title: "History",
      url: "/history",
    },
  ];

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
                transition
                duration-150
                ease-in-out
                flex
                items-center
                whitespace-nowrap
					 hover:bg-surface-hover
                dark: opacity-100
					 focus:shadow-focus
                `}
                style={{
                  borderRadius: "var(--border-radius)",
                  border:
                    location.pathname === item.url
                      ? "2px solid var(--primary-color)"
                      : "2px solid var(--surface-ground)",
                  outline: "0 none",
                  outlineOffset: "0",
                }}
                end
              >
                {item.title}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export default Navbar;
