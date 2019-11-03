#!/bin/sh

DIRIN=$1;
mkdir -p $DIRIN;
cp rdel rserver rstat rsub rutils.py simpbs_creat $DIRIN;
chmod -R 755 $DIRIN/rdel $DIRIN/rstat $DIRIN/rsub $DIRIN/rutils.py;
chmod -R 700 $DIRIN/simpbs_creat $DIRIN/rserver
$DIRIN/simpbs_creat $DIRIN;

chmod -R 755 $DIRIN/spool;
chmod -R 766 $DIRIN/spool/taskid $DIRIN/spool/taskid.bak $DIRIN/spool/tasks;
