import RoleCard from "./roleCard";

function RoleCalculator({ pool, setPool }) {
  // if weekending does not match with current week, show 'calculate roles' button
  const isCurrentWeek = (() => {
    const today = new Date();
    const firstDay = new Date(today.setDate(today.getDate() - today.getDay()));
    const lastDay = new Date(
      today.setDate(today.getDate() - today.getDay() + 6)
    );

    //TODO: Check in the last record in history from DB, if weekEnding matches current week
    return true;
  })();

  function selectHandler(id, user) {
    setPool((prevPool) => {
      return prevPool.map((role) => {
        return role.id === id ? { ...role, userSelected: user } : role;
      });
    });
  }

  return (
    <div>
      <div className="week-selector text-4xl flex gap-10 justify-center	mb-16">
        <button>&lt;</button>
        <h2>{isCurrentWeek ? "Current Week" : "Week "}</h2>
        <button>&gt;</button>
      </div>
      {pool.map((role) => {
        return (
          <RoleCard
            key={role.id}
            roleId={role.id}
            team={role.usersAvailabe}
            selected={role.userSelected}
            selectHandler={(user) => selectHandler(role.id, user)}
          />
        );
      })}
    </div>
  );
}

export default RoleCalculator;
