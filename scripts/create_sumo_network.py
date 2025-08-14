#!/usr/bin/env python3
"""Create basic SUMO network files compatible with sumo-rl."""

import os
from pathlib import Path


def create_network_file():
    """Create basic intersection network file."""
    network_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<net version="1.16" junctionCornerDetail="5" limitTurnSpeed="5.50" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/net_file.xsd">

    <location netOffset="100.00,100.00" convBoundary="0.00,0.00,200.00,200.00" origBoundary="-10000000000.00,-10000000000.00,10000000000.00,10000000000.00" projParameter="!"/>

    <edge id="1i" from="1" to="0" priority="78" type="highway.primary" spreadType="center" shape="0.00,95.20 92.00,95.20">
        <lane id="1i_0" index="0" allow="passenger" speed="13.89" length="92.00" shape="0.00,91.60 92.00,91.60"/>
        <lane id="1i_1" index="1" allow="passenger" speed="13.89" length="92.00" shape="0.00,94.80 92.00,94.80"/>
        <lane id="1i_2" index="2" allow="passenger" speed="13.89" length="92.00" shape="0.00,98.00 92.00,98.00"/>
    </edge>
    
    <edge id="1o" from="0" to="1" priority="78" type="highway.primary" spreadType="center" shape="108.00,104.80 200.00,104.80">
        <lane id="1o_0" index="0" allow="passenger" speed="13.89" length="92.00" shape="108.00,101.20 200.00,101.20"/>
        <lane id="1o_1" index="1" allow="passenger" speed="13.89" length="92.00" shape="108.00,104.40 200.00,104.40"/>
        <lane id="1o_2" index="2" allow="passenger" speed="13.89" length="92.00" shape="108.00,107.60 200.00,107.60"/>
    </edge>

    <edge id="2i" from="2" to="0" priority="78" type="highway.primary" spreadType="center" shape="104.80,200.00 104.80,108.00">
        <lane id="2i_0" index="0" allow="passenger" speed="13.89" length="92.00" shape="101.20,200.00 101.20,108.00"/>
        <lane id="2i_1" index="1" allow="passenger" speed="13.89" length="92.00" shape="104.40,200.00 104.40,108.00"/>
        <lane id="2i_2" index="2" allow="passenger" speed="13.89" length="92.00" shape="107.60,200.00 107.60,108.00"/>
    </edge>

    <edge id="2o" from="0" to="2" priority="78" type="highway.primary" spreadType="center" shape="95.20,92.00 95.20,0.00">
        <lane id="2o_0" index="0" allow="passenger" speed="13.89" length="92.00" shape="98.80,92.00 98.80,0.00"/>
        <lane id="2o_1" index="1" allow="passenger" speed="13.89" length="92.00" shape="95.60,92.00 95.60,0.00"/>
        <lane id="2o_2" index="2" allow="passenger" speed="13.89" length="92.00" shape="92.40,92.00 92.40,0.00"/>
    </edge>

    <junction id="0" type="traffic_light" x="100.00" y="100.00" incLanes="2i_0 2i_1 2i_2 1i_0 1i_1 1i_2" intLanes="" shape="99.60,108.00 109.20,108.00 109.64,105.78 110.20,105.00 110.64,103.56 110.96,101.44 111.16,98.67 108.00,98.00 105.78,98.44 105.00,99.00 103.56,99.44 101.44,99.78 98.67,100.00 92.00,100.40 92.44,103.56 93.00,104.33 93.44,105.78 93.78,107.89 94.00,110.67 99.60,108.00">
        <request index="0" response="000000000000" foes="000100010000" cont="0"/>
        <request index="1" response="000000000000" foes="111100110000" cont="0"/>
        <request index="2" response="000011000000" foes="110011110000" cont="0"/>
        <request index="3" response="100010000000" foes="100010000000" cont="0"/>
        <request index="4" response="000010000111" foes="100110000111" cont="0"/>
        <request index="5" response="011010000110" foes="011110000110" cont="0"/>
        <request index="6" response="000000000000" foes="010000000100" cont="0"/>
        <request index="7" response="000000000000" foes="110000111100" cont="0"/>
        <request index="8" response="000000000011" foes="110000110011" cont="0"/>
        <request index="9" response="000000100010" foes="000000100010" cont="0"/>
        <request index="10" response="000111100010" foes="000111100110" cont="0"/>
        <request index="11" response="000110011010" foes="000110011110" cont="0"/>
    </junction>

    <junction id="1" type="dead_end" x="0.00" y="95.20" incLanes="1o_0 1o_1 1o_2" intLanes="" shape="0.00,95.20 0.00,109.20 0.00,95.20"/>
    <junction id="2" type="dead_end" x="104.80" y="200.00" incLanes="2o_0 2o_1 2o_2" intLanes="" shape="104.80,200.00 90.80,200.00 104.80,200.00"/>

    <tlLogic id="0" type="static" programID="0" offset="0">
        <phase duration="31" state="GGGrrrGGGrrr"/>
        <phase duration="6" state="yyyrrryyyrrr"/>
        <phase duration="31" state="rrrGGGrrrGGG"/>
        <phase duration="6" state="rrryyyrrryyy"/>
    </tlLogic>

</net>'''
    
    return network_xml


def create_routes_file():
    """Create basic routes file."""
    routes_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">

    <!-- Vehicle types -->
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="55.55" guiShape="passenger"/>

    <!-- Routes -->
    <route id="route_ns" edges="2i 2o"/>
    <route id="route_sn" edges="1i 1o"/>
    <route id="route_ew" edges="1i 2o"/>
    <route id="route_we" edges="2i 1o"/>

    <!-- Traffic flows -->
    <flow id="flow_ns" route="route_ns" begin="0" end="3600" vehsPerHour="400" type="car"/>
    <flow id="flow_sn" route="route_sn" begin="0" end="3600" vehsPerHour="400" type="car"/>
    <flow id="flow_ew" route="route_ew" begin="0" end="3600" vehsPerHour="200" type="car"/>
    <flow id="flow_we" route="route_we" begin="0" end="3600" vehsPerHour="200" type="car"/>

</routes>'''
    
    return routes_xml


def create_config_file():
    """Create SUMO configuration file."""
    config_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">

    <input>
        <net-file value="single_intersection.net.xml"/>
        <route-files value="single_intersection.rou.xml"/>
    </input>

    <time>
        <begin value="0"/>
        <end value="3600"/>
        <step-length value="1"/>
    </time>

    <processing>
        <ignore-route-errors value="true"/>
    </processing>

    <routing>
        <device.rerouting.adaptation-steps value="18"/>
        <device.rerouting.adaptation-interval value="10"/>
    </routing>

    <report>
        <xml-validation value="never"/>
        <no-step-log value="true"/>
        <no-warnings value="true"/>
    </report>

    <gui_only>
        <gui-settings-file value="gui-settings.cfg"/>
    </gui_only>

</configuration>'''
    
    return config_xml


def create_gui_settings():
    """Create GUI settings file."""
    gui_settings = '''<viewsettings>
    <viewport y="100" x="100" zoom="800"/>
    <delay value="100"/>
    <scheme name="real world"/>
</viewsettings>'''
    
    return gui_settings


def main():
    """Create all SUMO files."""
    # Create sumo directory
    sumo_dir = Path("sumo")
    sumo_dir.mkdir(exist_ok=True)
    
    # Create network file
    with open(sumo_dir / "single_intersection.net.xml", "w") as f:
        f.write(create_network_file())
    print("Created single_intersection.net.xml")
    
    # Create routes file
    with open(sumo_dir / "single_intersection.rou.xml", "w") as f:
        f.write(create_routes_file())
    print("Created single_intersection.rou.xml")
    
    # Create config file
    with open(sumo_dir / "single_intersection.sumocfg", "w") as f:
        f.write(create_config_file())
    print("Created single_intersection.sumocfg")
    
    # Create GUI settings
    with open(sumo_dir / "gui-settings.cfg", "w") as f:
        f.write(create_gui_settings())
    print("Created gui-settings.cfg")
    
    print("\nSUMO network files created successfully!")
    print("Compatible with sumo-rl library!")
    print("You can now run:")
    print("python scripts/demo_sumo_rl.py --gui --episodes 3")
    print("python scripts/train_ppo.py --gui --episodes 50")


if __name__ == "__main__":
    main()