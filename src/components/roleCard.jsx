import { Dropdown } from "primereact/dropdown";
import { roles } from "./data/roles";

function RoleCard({ roleId, team, selected, selectHandler }) {
  const roleName = roles[roleId].name;
  const roleIcon = roles[roleId].icon;

  return (
    <div className="flex items-center p-5 gap-5">
      <div title={`${roleName}`}>{roleIcon}</div>
      <Dropdown
        value={selected}
        options={team}
        onChange={(e) => selectHandler(e.value)}
        placeholder="Select"
        filter
        showClear
        showFilterClear
      />
      {team.name}
    </div>
  );
}

export default RoleCard;
