import { TbBow } from "react-icons/tb";
import { BsEyeglasses, BsTrophy } from "react-icons/bs";
import { GiProtectionGlasses, GiGardeningShears } from "react-icons/gi";
import { VscMegaphone } from "react-icons/vsc";

export const roles = [
  {
    id: 0,
    code: "gar",
    name: "Gardener",
    description: "Gardener Description",
    icon: <GiGardeningShears className="icon" />,
    enabled: true,
  },
  {
    id: 1,
    code: "hun",
    name: "Hunter",
    description: "Hunter Description",
    icon: <TbBow className="icon" />,
    enabled: true,
  },
  {
    id: 2,
    code: "mas",
    name: "Master",
    description: "Master Description",
    icon: <BsTrophy className="icon" />,
    enabled: true,
  },
  {
    id: 3,
    code: "revT1",
    name: "Reviewer Tier 1",
    description: "Reviewer Tier 1 Description",
    icon: <GiProtectionGlasses className="icon" />,
    enabled: true,
  },
  {
    id: 4,
    code: "revT2",
    name: "Reviewer Tier 2",
    description: "Reviewer Tier 2 Description",
    icon: <BsEyeglasses className="icon" />,
    enabled: true,
  },
  {
    id: 5,
    name: "Reporter",
    code: "rep",
    description: "Reporter Description",
    icon: <VscMegaphone className="icon" />,
    enabled: true,
  },
];
