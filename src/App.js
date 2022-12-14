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
  const enabledRoles = roles.filter((role) => role.enabled);
  // Fetch team from database
  const team = [
    {
      id: 0,
      name: "user1",
      rolesAvailable: ["gar", "revT1", "revT2", "hun"],
      isAway: false,
      volunteer: "",
    },
    {
      id: 1,
      name: "user2",
      rolesAvailable: ["gar", "revT1", "revT2"],
      isAway: false,
      volunteer: "",
    },
    {
      id: 2,
      name: "user3",
      rolesAvailable: ["gar", "revT1", "revT2", "hun"],
      isAway: false,
      volunteer: "",
    },
    {
      id: 3,
      name: "user4",
      rolesAvailable: ["revT1", "revT2", "hun"],
      isAway: false,
      volunteer: "",
    },
    {
      id: 4,
      name: "user5",
      rolesAvailable: ["revT1", "revT2", "rep"],
      isAway: false,
      volunteer: "",
    },
    {
      id: 5,
      name: "user6",
      rolesAvailable: ["gar", "revT1", "revT2", "mas"],
      isAway: false,
      volunteer: "",
    },
    {
      id: 6,
      name: "user7",
      rolesAvailable: ["gar", "revT1", "revT2", "hun"],
      isAway: false,
      volunteer: "",
    },
    {
      id: 7,
      name: "user8",
      rolesAvailable: ["revT1", "revT2", "mas"],
      isAway: false,
      volunteer: "",
    },
  ];

  // Fetch history from database
  let historyDb = [
    {
      weekEnding: "2022-10-16",
      userRoles: [
        { role: "gar", user: "user5" },
        { role: "hun", user: "user6" },
        { role: "mas", user: "user1" },
        { role: "revT1", user: "user2" },
        { role: "revT2", user: "user3" },
        { role: "rep", user: "user4" },
      ],
    },
    {
      weekEnding: "2022-10-23",
      userRoles: [
        { role: "gar", user: "user6" },
        { role: "hun", user: "user1" },
        { role: "mas", user: "user2" },
        { role: "revT1", user: "user3" },
        { role: "revT2", user: "user4" },
        { role: "rep", user: "user5" },
      ],
    },
    {
      weekEnding: "2022-10-30",
      userRoles: [
        { role: "gar", user: "user1" },
        { role: "hun", user: "user2" },
        { role: "mas", user: "user3" },
        { role: "revT1", user: "user4" },
        { role: "revT2", user: "user5" },
        { role: "rep", user: "user6" },
      ],
    },
    {
      weekEnding: "2022-11-06",
      userRoles: [
        { role: "gar", user: "user2" },
        { role: "hun", user: "user3" },
        { role: "mas", user: "user4" },
        { role: "revT1", user: "user5" },
        { role: "revT2", user: "user6" },
        { role: "rep", user: "user1" },
      ],
    },
  ];

  const historyLength = historyDb.length;

  // Build pool state object (which will be pushed in the history database)
  const pool = enabledRoles.map((role) => ({
    id: role.id,
    roleCode: role.code,
    roleName: role.name,
    usersAvailable: getUsers(role.code),
    volunteer: undefined,
    userSelected: undefined,
  }));

  // Build user history record
  const userHistory = team.map((user) => ({
    id: user.id,
    name: user.name,
    lastDoneRoles: getUserHistory(user.name),
  }));

  function getUserHistory(userName) {
    // Initialize the array with the max value
    let tempHistoryArray = enabledRoles.map((role) => ({
      id: role.id,
      role: role.code,
      lastDone: historyLength,
    }));

    for (const [index, week] of historyDb.entries()) {
      const key = historyLength - (index + 1); // key represents the week number, last entries are the most recent weeks
      week.userRoles.forEach((role) => {
        if (role.user === userName) {
          // Find role entry in inizialized array
          const elemIndex = tempHistoryArray.findIndex(
            (elem) => elem.role === role.role
          );
          // if found assign last done to the week number value
          if (elemIndex !== -1) tempHistoryArray[elemIndex].lastDone = key;
        }
      });
    }
    return tempHistoryArray;
  }

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
            element={
              <RoleCalculator
                pool={poolState}
                setPool={setPoolState}
                userHistory={userHistory}
                enabledRoles={enabledRoles}
              />
            }
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
