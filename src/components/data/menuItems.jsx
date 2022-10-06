import RoleCalculator from "../roleCalculator";
import TeamList from "../teamList";
import RolesList from "../rolesList";
import History from "../history";

export const MenuItems = [
  {
    Title: "Home",
    url: "/",
    component: <RoleCalculator />,
  },
  {
    Title: "Team",
    url: "/team",
    component: <TeamList />,
  },
  {
    Title: "Roles",
    url: "/roles",
    component: <RolesList />,
  },
  {
    Title: "History",
    url: "/history",
    component: <History />,
  },
];
