const TableHistory = ({ userHistory, selectHandler, pool }) => {
  function tableRow(user) {
    return (
      <tr key={user.id}>
        <td className="p-5">{user.name}</td>
        {pool.map((role) => tableTd(user, role))}
      </tr>
    );
  }

  function tableTd(user, role) {
    const poolElement = pool.find((poolRole, index) => poolRole.id === role.id);
    const isAvailable = poolElement.usersAvailable.includes(user.name);
    const isSelected = poolElement.userSelected === user.name;
    return (
      <td key={`${user.id}${role.id}`}>
        <button
          type="button"
          className="p-5 rounded enabled:hover:bg-surface-hover disabled:opacity-25 focus:shadow-focus"
          style={{
            border: isSelected
              ? "2px solid var(--primary-color)"
              : "2px solid var(--surface-ground)",
            outline: "0 none",
            outlineOffset: "0",
          }}
          onClick={() => selectHandler(role.id, user.name)}
          disabled={!isAvailable}
        >
          {isAvailable
            ? user.lastDoneRoles.find(
                (lastDoneRole) => lastDoneRole.role === role.roleCode
              ).lastDone
            : "ND"}
        </button>
      </td>
    );
  }

  return (
    <table>
      <thead>
        <tr>
          <th className="p-5">User</th>
          {pool.map((role) => (
            <th key={role.id} className="p-5">
              {role.roleName}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>{userHistory.map((user) => tableRow(user))}</tbody>
    </table>
  );
};

export default TableHistory;
