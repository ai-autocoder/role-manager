import React, { useState } from "react";
import User from "./data/user";

function Users() {
  const [userData, setUserData] = useState(null);
  React.useEffect(() => {
    async function getUserData() {
      let response = await fetch("/api");
      response = await response.json();
      setUserData(response.message);
    }
    getUserData();
  }, []);

  return (
    <div>
      <p>Users:</p>
      {userData &&
        userData.map(({ ID, Name, IsAbsent, Volunteers, TeamId }) => (
          <User name={Name} key={ID} />
        ))}
    </div>
  );
}

export default Users;
