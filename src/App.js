import Navbar from "./components/navbar";
import { Route, Routes } from "react-router-dom";
import { useState } from "react";
import { roles } from "./components/data/roles";
import RoleCalculator from "./components/roleCalculator";
import TeamList from "./components/teamList";
import RolesList from "./components/rolesList";
import History from "./components/history";

import "primereact/resources/themes/lara-dark-teal/theme.css"; //theme
import "primereact/resources/primereact.min.css"; //core css
import "primeicons/primeicons.css"; //icons

function App() {
  // fetch team from database
  const team = [
    {
      name: "User1",
      rolesAvailable: ["gar", "revT1", "revT2", "hun"],
      isAway: false,
      volunteer: "",
    },
    {
      name: "User2",
      rolesAvailable: ["gar", "revT1", "revT2"],
      isAway: false,
      volunteer: "",
    },
    {
      name: "User3",
      rolesAvailable: ["gar", "revT1", "revT2", "hun"],
      isAway: false,
      volunteer: "",
    },
    {
      name: "User4",
      rolesAvailable: ["revT1", "revT2", "hun"],
      isAway: false,
      volunteer: "",
    },
    {
      name: "User5",
      rolesAvailable: ["revT1", "revT2", "rep"],
      isAway: false,
      volunteer: "",
    },
    {
      name: "User6",
      rolesAvailable: ["gar", "revT1", "revT2", "mas"],
      isAway: false,
      volunteer: "",
    },
    {
      name: "User7",
      rolesAvailable: ["gar", "revT1", "revT2", "hun"],
      isAway: false,
      volunteer: "",
    },
    {
      name: "User8",
      rolesAvailable: ["revT1", "revT2", "mas"],
      isAway: false,
      volunteer: "",
    },
  ];

  // fetch history from database
  let historyDb = [
    {
      weekEnding: "2022-10-16",
      gardener: "",
      hunter: "",
      master: "",
      revT1: "",
      revT2: "",
      reporter: "",
    },
    {
      weekEnding: "2022-10-09",
      gardener: "",
      hunter: "",
      master: "",
      revT1: "",
      revT2: "",
      reporter: "",
    },
  ];

  // calculate event

  // pool object (which will be pushed in the history database)
  const pool = roles.map((role) => ({
    id: role.id,
    roleCode: role.code,
    usersAvailabe: getUsers(role.code),
    volunteer: undefined,
    userSelected: undefined,
  }));

  function getUsers(roleCode) {
    return team.flatMap((user) =>
      user.rolesAvailable.includes(roleCode) ? user.name : []
    );
  }

  const [poolState, setPoolState] = useState(pool);

  return (
    <div className="container min-h-screen min-w-full p-4">
      <Navbar />
      <main>
        <Routes>
          <Route
            path="/"
            element={<RoleCalculator pool={poolState} setPool={setPoolState} />}
          />
          <Route path="/team" element={<TeamList />} />
          <Route path="/roles" element={<RolesList />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
