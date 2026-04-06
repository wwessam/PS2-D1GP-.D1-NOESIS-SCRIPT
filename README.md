# ORIGINAL SCRIPT MADE BY LEEAO https://github.com/leeao
# FORK BY RAGHID0401
# PS2 D1GP .D1 TRACK RIPPING NOESIS SCRIPT
edited script to read world sections that consist of plane sections and atomic sections and bin mesh PLG.
for now the script only reads world sections at the root of the dff. it should skip clumps just fine.
also removed anything related to reading textures because you can just rip the textures from maps with magicTXD if you rename the .d1 file to a .txd lol.




# Usage
Put the *.py script in the Noesis\plugin\python directory.

PLEASE STRIP TXD FROM .D1 FILE FIRST.
YOU CAN ALSO OPEN THE FILE IN RWANALYZE AND DELETE THE FIRST TXD SECTION BUT ONLY DO THIS IF OTHER SECTIONS CAN BE SEEN.

IF YOU CAN ONLY SEE 1 TXD SECTION IN RW ANALYZE YOU WILL NEED TO USE A HEX EDITOR TO DELETE THAT FIRST TXD SECTION.
 
USE A HEX EDITOR AND SET YOUR OFFSET TO THE SECOND 32 BIT INTEGER RIGHT AFTER THE FILE STARTS.
MOVE TO THAT OFFSET AND THEN SCROLL A LITTLE BIT FORWARD UNTIL YOU SEE 10 00 00 00. THATS WHERE YOU WANT THE NEW FILE TO START.
SELECT EVERYTHING BEFORE IT AND DELETE AND SAVE AS NEW. THIS NEW FILE SHOULD BE OPENABLE IN NOESIS WITH THE SCRIPT. 
AND ALSO NOW YOU WILL SEE ALL SECTIONS IN RWANALYZE.


# Noesis
Noesis:
http://www.richwhitehouse.com/index.php?content=inc_projects.php&showproject=91
