namespace ObjectFlow
{
  const InstanceTemplate instance_list[] = {
    {43000, 0, InputLinkType, 0, linkType, (AnyValueType){.linkType={43001,0}} },
    {43000, 0, CurrentValueType ,0, integerType, (AnyValueType){.integerType=0} },
    {43000, 0, OutputLinkType, 0, linkType, (AnyValueType){.linkType={43002,0}} },

    {43001, 0, OutputValueType ,0, integerType, (AnyValueType){.integerType=0} },
    
    {43002, 0, InputValueType ,0, integerType, (AnyValueType){.integerType=0} },
  };
}