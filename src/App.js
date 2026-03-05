import React, { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { roles } from "./components/data/roles";
import History from "./components/history";
import Navbar from "./components/navbar";
import RoleCalculator from "./components/roleCalculator";
import RolesList from "./components/rolesList";
import TeamList from "./components/teamList";
import Users from "./components/users";

import "primeicons/primeicons.css"; //icons
import "primereact/resources/primereact.min.css"; //core css
import "primereact/resources/themes/lara-dark-teal/theme.css"; //theme

function App() {
	const enabledRoles = roles.filter((role) => role.enabled);
	// Fetch team from database
	const team = [
		{
			id: 0,
			name: "user1",
			isAway: false,
			volunteer: "",
			rolesAvailable: [
				{
					roleCode: "role_1",
					motivationFactor: 1,
				},
				{
					roleCode: "role_4",
					motivationFactor: 1,
				},
				{
					roleCode: "role_5",
					motivationFactor: 1,
				},
				{
					roleCode: "role_2",
					motivationFactor: 1,
				},
			],
		},
		{
			id: 1,
			name: "user2",
			isAway: false,
			volunteer: "",
			rolesAvailable: [
				{
					roleCode: "role_1",
					motivationFactor: 1,
				},
				{
					roleCode: "role_4",
					motivationFactor: 1,
				},
				{
					roleCode: "role_5",
					motivationFactor: 1,
				},
			],
		},
		{
			id: 2,
			name: "user3",
			rolesAvailable: [
				{
					roleCode: "role_1",
					motivationFactor: 1,
				},
				{
					roleCode: "role_4",
					motivationFactor: 1,
				},
				{
					roleCode: "role_5",
					motivationFactor: 1,
				},
				{
					roleCode: "role_2",
					motivationFactor: 1,
				},
			],
			isAway: false,
			volunteer: "",
		},
		{
			id: 3,
			name: "user4",
			rolesAvailable: [
				{
					roleCode: "role_4",
					motivationFactor: 1,
				},
				{
					roleCode: "role_5",
					motivationFactor: 1,
				},
				{
					roleCode: "role_2",
					motivationFactor: 1,
				},
			],
			isAway: false,
			volunteer: "",
		},
		{
			id: 4,
			name: "user5",
			rolesAvailable: [
				{
					roleCode: "role_4",
					motivationFactor: 1,
				},
				{
					roleCode: "role_5",
					motivationFactor: 1,
				},
				{
					roleCode: "role_6",
					motivationFactor: 1,
				},
			],
			isAway: false,
			volunteer: "",
		},
		{
			id: 5,
			name: "user6",
			rolesAvailable: [
				{
					roleCode: "role_4",
					motivationFactor: 1,
				},
				{
					roleCode: "role_5",
					motivationFactor: 1,
				},
				{
					roleCode: "role_1",
					motivationFactor: 1,
				},
				{
					roleCode: "role_3",
					motivationFactor: 1,
				},
			],
			isAway: false,
			volunteer: "",
		},
		{
			id: 6,
			name: "user7",
			rolesAvailable: [
				{
					roleCode: "role_4",
					motivationFactor: 1,
				},
				{
					roleCode: "role_5",
					motivationFactor: 1,
				},
				{
					roleCode: "role_2",
					motivationFactor: 1,
				},
				{
					roleCode: "role_1",
					motivationFactor: 1,
				},
			],
			isAway: false,
			volunteer: "",
		},
		{
			id: 7,
			name: "user8",
			rolesAvailable: [
				{
					roleCode: "role_4",
					motivationFactor: 1,
				},
				{
					roleCode: "role_5",
					motivationFactor: 1,
				},
				{
					roleCode: "role_3",
					motivationFactor: 1,
				},
			],
			isAway: false,
			volunteer: "",
		},
	];
	// Fetch history from database
	let historyDb = [
		{
			weekEnding: "2022-10-16",
			userRoles: [
				{ role: "role_1", user: "user5" },
				{ role: "role_2", user: "user6" },
				{ role: "role_3", user: "user1" },
				{ role: "role_4", user: "user2" },
				{ role: "role_5", user: "user3" },
				{ role: "role_6", user: "user4" },
			],
		},
		{
			weekEnding: "2022-10-23",
			userRoles: [
				{ role: "role_1", user: "user6" },
				{ role: "role_2", user: "user1" },
				{ role: "role_3", user: "user2" },
				{ role: "role_4", user: "user3" },
				{ role: "role_5", user: "user4" },
				{ role: "role_6", user: "user5" },
			],
		},
		{
			weekEnding: "2022-10-30",
			userRoles: [
				{ role: "role_1", user: "user1" },
				{ role: "role_2", user: "user2" },
				{ role: "role_3", user: "user3" },
				{ role: "role_4", user: "user4" },
				{ role: "role_5", user: "user5" },
				{ role: "role_6", user: "user6" },
			],
		},
		{
			weekEnding: "2022-11-06",
			userRoles: [
				{ role: "role_1", user: "user2" },
				{ role: "role_2", user: "user3" },
				{ role: "role_3", user: "user4" },
				{ role: "role_4", user: "user5" },
				{ role: "role_5", user: "user6" },
				{ role: "role_6", user: "user1" },
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

	function assignRoles() {
		const assignmentChart = [];

		// For each role, loop through the available users to build the assignmentChart scores
		pool.forEach((role) => {
			const roleCode = role.roleCode;
			const assignmentChartTemp = {
				roleCode,
				users: []
			};

			role.usersAvailable.forEach((user) => {
				// Find user in userHistory array
				const userIndex = userHistory.findIndex(
					(userHistory) => userHistory.name === user
				);
				// Find role in userHistory.lastDoneRoles array
				const roleIndex = userHistory[userIndex].lastDoneRoles.findIndex(
					(role) => role.role === roleCode
				);
				const lastDone = userHistory[userIndex].lastDoneRoles[roleIndex].lastDone;

				// get motivationFactor
				const matchingUser = team.find(obj => obj.name === user);
				const motivationFactor = matchingUser.rolesAvailable.find(role => role.roleCode === roleCode).motivationFactor;

				// get experienceFactor (temporarily set to 1)
				const experienceFactor = 1;

				let score = (lastDone * motivationFactor) + experienceFactor;
				assignmentChartTemp.users.push({ user, score });
			});
			assignmentChart.push(assignmentChartTemp);
		});
		
		// Sort users array by the score value descending 
		assignmentChart.forEach((role) => {
			role.users.sort((a, b) => b.score - a.score);
		});
		
		// console.log(JSON.stringify(assignmentChart));
		console.log(assignmentChart);
		//TODO:
		// Sort roles array by number of users available (increasing)
		//  const sortedPool = pool.sort((a, b) => {
		//    return a.usersAvailable.length - b.usersAvailable.length;
		//  });

		// Now set the state assignedUser 
      // selectHandler(role.id, assignedUser.name);
}

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
    const filteredTeam = team.filter((member) =>
      member.rolesAvailable.some((role) => role.roleCode === roleCode)
    );
    return filteredTeam.map((member) => member.name);
  }

  const [poolState, setPoolState] = useState(pool);

  function selectHandler(roleId, user) {
    setPoolState((poolState) =>
      poolState.map((role) =>
        role.id === roleId ? { ...role, userSelected: user } : role
      )
    );
  }

  return (
    <div className="container min-w-full min-h-screen p-4">
      <Navbar />
      <main>
        <Routes>
          <Route
            path="/"
            element={
              <RoleCalculator
                pool={poolState}
                setPool={selectHandler}
                userHistory={userHistory}
                enabledRoles={enabledRoles}
                assignHandler={assignRoles}
              />
            }
          />
          <Route path="/team" element={<TeamList />} />
          <Route path="/roles" element={<RolesList />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>

      <Users />
    </div>
  );
}

export default App;
