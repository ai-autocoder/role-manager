import { TbBow } from "react-icons/tb";
import { BsEyeglasses, BsTrophy } from "react-icons/bs";
import { GiProtectionGlasses, GiGardeningShears } from "react-icons/gi";
import { VscMegaphone } from "react-icons/vsc";

export const roles = [
  {
    name: "Gardener",
    code: "gar",
    description: "Gardener Description",
    icon: <GiGardeningShears className="icon" />,
  },
  {
    name: "Hunter",
    code: "hun",
    description: "Hunter Description",
    icon: <TbBow className="icon" />,
  },
  {
    name: "Master",
    code: "mas",
    description: "Master Description",
    icon: <BsTrophy className="icon" />,
  },
  {
    name: "Reviewer Tier 1",
    code: "revT1",
    description: "Reviewer Tier 1 Description",
    icon: <GiProtectionGlasses className="icon" />,
  },
  {
    name: "Reviewer Tier 2",
    code: "revT2",
    description: "Reviewer Tier 2 Description",
    icon: <BsEyeglasses className="icon" />,
  },
  {
    name: "Reporter",
    code: "rep",
    description: "Reporter Description",
    icon: <VscMegaphone className="icon" />,
  },
];
