# foamClean
Utility for openFOAM to remove timesteps or fields from decomposed cases. Sometimes you need to delete specific timesteps or fields from a decomposed openFOAM case. Maybe you went too fine with your writeInterval option, or maybe you have tight space restrictions and you want to remove unnecessary fields as you go. This is the tool for you!

# Installation
Both Python 3 and Python 2 are supported since some of the older clusters tend to not have Python 3 available. <br />
1) First, pull the code from the Github repo: <br />
`git clone https://github.com/tvdmitrii/foamClean.git`
2) Setup an alias for convenience of use. Add the following line at the end of your */home/USERNAME/.bashrc* file:  <br />
Python 3: `alias foamClean='python3 PATH_TO_FOAMCLEAN/foamClean.py'` <br />
Python 2: `alias foamClean='python2 PATH_TO_FOAMCLEAN/foamClean_py2.py'`

3) Relog and you are done! Use either from your case folder: <br />
`foamClean fields alpha1 --sim` <br />
or from anywhere else: <br />
`foamClean fields alpha1 --sim --path ./mycase`

# Be careful
There can be days, weeks or even months of simulation time on the line.
1) Try sampleCases provided to get familiar with the utility
2) Pay close attention to the information the utility gives before pulling the trigger
3) Use `--sim` option to run a simulation that will print file/directory names to be deleted

# Options
## Timesteps Mode
In timesteps mode you specify which timesteps you would like to **REMOVE** from all processorN folders. I tried to make it flexible, so there are a few options: <br />
* Specifying range of indices
  * `timesteps --index i j` removes timesteps that have index `ind` in a sorted timestep list satisfy condition `i <= ind < j`
  * `timesteps --index i`   removes timesteps tha have index `ind` in a sorted timestep list satisfy condition `i <= ind`
* Specifying list of indices
  * `timesteps --indexList i j k...` removes timesteps that have one of the specified indices in a sorted timestep list
* Specifying range of times
  * `timesteps --time t1 t2` removes timesteps that have time `time` satisfy condition `t1 <= time < t2`
  * `timesteps --time t1`   removes timesteps that have time `time` satisfy condition `t1 <= ind`
* Specifying list of times
  * `timesteps --timeList t1 t2 t3...` removes timesteps that have one of the specified times  <br />
**Note** that indices can be negative. For example, `-1` specifies the last timestep
 
## Fields Mode
In fields mode you specify which fields you would like to **KEEP**. By default, it affects all the timesteps in all the processor directories except for the zero timestep (in case you want to start over the simulation) and the last timestep (in case you want to continue the simulation later).
* `fields field1 field2 ...` removes all OTHER fields EXCEPT for *field1, field2...* according to default behavior
* `fields field1 --removeZero` removes all OTHER fields EXCEPT for *field1* according to default behavior plus affects the zero timestep
* `fields field1 --removeLast` removes all OTHER fields EXCEPT for *field1* according to default behavior plus affects the last timestep
* `fields field1 --removeZero --removeLast` removes all OTHER fields EXCEPT for *field1* according to default behavior plus affects the zero and last timesteps
**Note** that the utility automatically detects whether you are using compression and deals with ".gz" at the end of the field names.

## Universal Options
* `--sim` simulates delition process and only shows paths to be removed
* `--path` specifies path to a case. If omitted the default path is `./`
* `--force` skips use confirmation for deletion

# Screenshot
This is a screenshot from an **older verison**. The current version you do NOT specify *alpha1.gz*. You just provide the name of the field like *alpha1*. Also, the current version lists which fields will be removed, in addition to listing the fields to be kept.
![foamClean_showcase](https://user-images.githubusercontent.com/21278768/129247473-bb7d9112-32b9-4155-a2f8-6a67772867b4.png)
