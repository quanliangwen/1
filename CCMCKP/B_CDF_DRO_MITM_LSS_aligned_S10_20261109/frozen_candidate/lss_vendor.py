import numpy as np
import time,heapq,random
from random import choice
max_K=10
_alpha=.7
UpConfidenceLevel=.995

class Factor:

    def __init__(self, factor_id, cost, value, sample_filepath, big_sample_filepath=None):
        self.id = factor_id  # 独特id
        self.cost = cost
        self.value = value
        self.sample_filepath = sample_filepath  # sample对应的路径
        self.samples = np.loadtxt(sample_filepath)  # 采样数据，ndarray类  
        self.big_sample_filepath = big_sample_filepath  # 大规模采样对应的路径

        self._sample_min = None
        self._sample_max = None

        self._sample_mean = None
        self._sample_var = None
        self._sample_std = None
        self._big_samples = None #  np.loadtxt(big_sample_filepath)

        self._moments_min = None
        self._moments_origin = None
        # self._rnd_indices = np.arange(len(self.samples))

        self.weight = None
        self.utility = None
        self.increment = None

    def resample_once(self):
        # 采样一次，返回采样结果 (长度为1的ndarray)
        return self.resample_multi(1)

    def resample_multi(self, sample_number):
        # 采样 sample_number 次, 返回采样结果 (长度为 sample_number 的ndarray)
        _idx = np.random.randint(0, len(self.samples) - 1, sample_number)

        return self.samples[_idx]

    def resample_big_multi(self, sample_number):
        # 采样 sample_number 次, 返回采样结果 (长度为 sample_number 的ndarray)
        _idx = np.random.randint(0, len(self._big_samples) - 1, sample_number)

        return self._big_samples[_idx]

    # 创建只读属性
    @property
    def sample_min(self):
        # 采样最小值
        if self._sample_min is None:
            self._sample_min = np.min(self.samples)

        return self._sample_min

    @property
    def sample_max(self):
        # 采样最大值
        if self._sample_max is None:
            self._sample_max = np.max(self.samples)

        return self._sample_max

    @property
    def sample_mean(self):
        # 采样均值
        if self._sample_mean is None:
            self._sample_mean = np.mean(self.samples)

        return self._sample_mean

    @property
    def sample_var(self):
        # 采样方差
        if self._sample_var is None:
            self._sample_var = np.var(self.samples)

        return self._sample_var

    @property
    def sample_std(self):
        # 采样标准差
        if self._sample_std is None:
            self._sample_std = np.std(self.samples,ddof=1)

        return self._sample_std

    @property
    def big_samples(self):
        # 大规模采样，华为给真实数据后这项无用
        if self._big_samples is None:
            self._big_samples = np.loadtxt(self.big_sample_filepath)

        return self._big_samples

    def n_moment_min(self, K):
        # 计算减去最小值的1~K阶矩
        sample_size = len(self.samples)
        _aux_matrix = np.ones((2, sample_size))
        moments_list = np.ones(K + 1)

        for k in range(1, K + 1): # 1 to K
            _cur_idx = k % 2
            _prev_idx = 1 - _cur_idx
            _aux_matrix[_cur_idx] = (self.samples - self.sample_min) * _aux_matrix[_prev_idx]

            moments_list[k] = np.mean(_aux_matrix[_cur_idx])

        return moments_list

    def n_moment_of_origin(self, K):
        # 计算1~K阶原点矩
        sample_size = len(self.samples)
        _aux_matrix = np.ones((2, sample_size))
        moments_list = np.ones(K + 1)

        for k in range(1, K + 1): # 1 to K
            _cur_idx = k % 2
            _prev_idx = 1 - _cur_idx
            _aux_matrix[_cur_idx] = self.samples * _aux_matrix[_prev_idx]

            moments_list[k] = np.mean(_aux_matrix[_cur_idx])

        return moments_list

    @property
    def moments_min(self):
        # 减去最小值的1~K阶矩
        if self._moments_min is None:
            self._moments_min = self.n_moment_min(max_K)

        return self._moments_min

    @property
    def moments_origin(self):
        # 1~K阶原点矩
        if self._moments_origin is None:
            self._moments_origin = self.n_moment_of_origin(max_K)

        return self._moments_origin

    def set_weight(self,weight):
        self.weight = weight

    def set_utility(self,utility):
        self.utility = utility

    def set_increment(self,increment):
        self.increment = increment

    def get_index_sample(self,_l):
        # 返回数据中第L大的数据，最大为0，最小为L-1
        return np.sort(self.samples)[::-1][_l]

def Solution_Initialization(node_resort,param,order):

    node_id_list = [i for i in range(int(param[0]))]   
    Init_solution = np.zeros(len(node_id_list), dtype=int)

    for node_id in node_id_list:
        # 取出按照排好序的每个node中的第一个factor，即对应属性最大的factor
        Init_solution[node_id] = node_resort[node_id][order]
    
    return Init_solution

def Solution_Evaluation(eval_func, Solution, T_max, factor_id2obj, CL, param, MC_sample_size, quick_check_list):

    factor_list = []
    for factor_id in Solution:
        factor_list.append(factor_id2obj[factor_id])

    return eval_func(factor_list, T_max, MC_sample_size, CL, param, quick_check_list)

def confidence_list_evaluation(ConfidencRecord, Eval_func, solution, T_max, fi, CL, param, MC_sample_size, quick_check_list):
    # c_array格式：np.array([[eval_times,average_p,solution[0],...,solution[12]],...,[eval_times,average_p,solution[0],...,solution[12]]])
    # 评估次数：ConfidencRecord[:][0]
    # 平均置信度： ConfidencRecord[:][1]
    # 解： ConfidencRecord[:][2:]
    _index = np.where(np.equal(ConfidencRecord[:,2:],solution).all(1)==True)[0]

    if _index.size:
        # 在c_array中，找出Index并检查eval_times
        s_index = _index[0]
        if ConfidencRecord[s_index][0] == 3:
            Eval_times = 1
            return ConfidencRecord[s_index][1],Eval_times
        
        else:
            p = Solution_Evaluation(Eval_func, solution, T_max, fi, CL, param, MC_sample_size, quick_check_list)
            ConfidencRecord[s_index][1] = (ConfidencRecord[s_index][0]*ConfidencRecord[s_index][1] + p)/(ConfidencRecord[s_index][0]+1)
            ConfidencRecord[s_index][0] += 1
            Eval_times = 1
            return ConfidencRecord[s_index][1],Eval_times
        

    else:
        # 不在c_array中，增添
        p = Solution_Evaluation(Eval_func, solution, T_max, fi, CL, param, MC_sample_size, quick_check_list)
        s_list = [1,p]
        s_list.extend(solution)
        ConfidencRecord = np.vstack((ConfidencRecord,s_list))
        Eval_times = 1
        
        return p, Eval_times

def solution_cost(solution,factor_id2obj):
    cost = 0
    for _factor_id in solution:
        _factor = factor_id2obj[_factor_id]
        cost += _factor.cost
    
    return cost

def Construct_Procedure(Eval_func, node_resort_w, node_resort_u, fi, threshold_p, T_max, param, MC_sample_size, quick_check_list):

    Eval_times = 0
    Solution = Solution_Initialization(node_resort_u, param, 0)
    _St = np.copy(Solution)
    available_S = np.copy(Solution)
    _pt = Solution_Evaluation(Eval_func, _St, T_max, fi, threshold_p, param, MC_sample_size, quick_check_list)
    stopping_condition = -np.ones(len(available_S),int)
    select_node = -1
    Eval_times += 1
    Tem_solution = [[solution_cost(available_S,fi),_pt,available_S,Eval_times]]
    while 1:

        factor_list = []
        for factor_id in _St:
            factor_list.append(fi[factor_id])

        solution_weight = [factor.weight for factor in factor_list]

        for i in range(len(available_S)):
            if available_S[i] == -1:
                solution_weight[i] = -1

        select_node = np.argsort(solution_weight)[-1] # 当前解中weight最大的factor所在的node
        # print(select_node)
        select_factor = _St[select_node]
        # print(select_factor)

        # 找到weight矩阵中比factor小的下一个因子，对应到utility矩阵中的序号
        if node_resort_w[select_node].index(select_factor) < len(node_resort_w[select_node])-1: 

            _St[select_node] = node_resort_w[select_node][node_resort_w[select_node].index(select_factor)+1]
            _pt = Solution_Evaluation(Eval_func, _St, T_max, fi, threshold_p, param, MC_sample_size, quick_check_list)
            c_ = solution_cost(_St,fi)
            print("当前解：",c_ ,_pt,_St)
            Eval_times += 1
            Tem_solution.append([c_ ,_pt,_St,Eval_times])
            if _pt >= threshold_p:
                # print("Yeah!")
                break
        else:
            # 随后的循环不再替换本次的select_node
            available_S[select_node] = -1
            if (available_S == stopping_condition).all():
                print("Warning: 没有找到可行解, 初始解设为每个class下最小weight的item!")
                _St = Solution_Initialization(node_resort_w, param, -1)
                break   

    init_feasible_Solution = _St
    init_obj_cost = solution_cost(_St,fi)
    init_p = _pt

    return init_feasible_Solution, init_obj_cost, init_p, Eval_times, Tem_solution

def Local_Swap_Search(EvaluationFunction, Solution, p, node_resort_v, FactortoObject, CL, T_max,param, MonteCarloTimes, QuickCheckList, Eval_times,TemSolutionList,ConfidenceRecord, CostList,MonteCarloList):
    node_list = [i for i in range(int(param[0]))]
    _St,_S = np.copy(Solution), np.copy(Solution)
    _p = p
    random.shuffle(node_list)

    for node_id in node_list:
        select_factor = _St[node_id]
        # 遍历value矩阵中比factor大的所有因子
        index_ = node_resort_v[node_id].index(select_factor)

        for factor_id in node_resort_v[node_id][:index_][::-1]:
            _St[node_id] = factor_id
            # _pt, _t = confidence_list_evaluation(ConfidenceRecord, EvaluationFunction, _St, T_max, FactortoObject, CL, param, MonteCarloTimes, QuickCheckList)
            _pt = Solution_Evaluation(EvaluationFunction, _St, T_max, FactortoObject, CL, param, MonteCarloTimes, QuickCheckList)
            Eval_times += 1
            if _pt >= CL:
                _S = np.copy(_St)   # 尽可能找到最大value且满足置信度约束的那个因子
                _p = _pt
                _c = solution_cost(_S,FactortoObject)
                FeasibleSolutionList(_S,_c,_p,CostList,MonteCarloList)
                TemSolutionList.append([_c ,_p,_S,Eval_times])
                break               # node_resort_v从大到小排列，找到的第一个可行item即可跳出    
        _St = np.copy(_S)   # 更新_St

    feasible_Solution = _S
    obj_cost = solution_cost(_S,FactortoObject)
    p = _p
    return  obj_cost,p,feasible_Solution,Eval_times

def Degrade_(EvaluationFunction, Solution, _pp, node_resort_w ,FactortoObject, CL, T_max, param, MonteCarloTimes, ex_node, ex_factor, QuickCheckList, ConfidenceRecord):

    _St = np.copy(Solution)
    Eval_times = 0

    node_id = choice([i for i in range(int(param[0])) if i not in ex_node]) # 随机选择一个禁忌集外的node
    node_factor_ex =[_St[node_id]]

    _St[node_id] = choice([factor for factor in node_resort_w[node_id] if factor not in ex_factor])   # 随机选择一个非原因子的因子  
    node_factor_ex.append(_St[node_id]) # 更新当前node的禁忌集
    _pt = Solution_Evaluation(EvaluationFunction, _St, T_max, FactortoObject, CL, param, MonteCarloTimes, QuickCheckList)
    Eval_times += 1

    while _pt < CL:

        if len(node_factor_ex) < len(node_resort_w[node_id]):

            _St[node_id] = choice([factor for factor in node_resort_w[node_id] if factor not in node_factor_ex])   # 随机选择一个非原因子的因子  
            node_factor_ex.append(_St[node_id]) # 更新当前node的禁忌集
            # _pt, _t = confidence_list_evaluation(ConfidenceRecord, EvaluationFunction, _St, T_max, FactortoObject, CL, param, MonteCarloTimes, QuickCheckList)
            _pt = Solution_Evaluation(EvaluationFunction, _St, T_max, FactortoObject, CL, param, MonteCarloTimes, QuickCheckList)
            Eval_times += 1

        elif len(ex_node)<int(param[0])-1:
            # 该node除了原factor外所有其他factor都不可行，恢复原始解，并更换Node
            ex_node.append(node_id) # 更新node的禁忌集        
            _, _pt, _St, eval= Degrade_(EvaluationFunction, Solution, _pp, node_resort_w ,FactortoObject, CL, T_max, param,MonteCarloTimes,ex_node,ex_factor, QuickCheckList,ConfidenceRecord)
            Eval_times = eval

        else:
            # print("当前输入不能做任何的degrade!!!\n")
            _pt = _pp
            return solution_cost(Solution,FactortoObject),_pt,Solution,Eval_times

    # print(f"The Evaluation times of Degrade_ procedure is {Eval_times}")
    return solution_cost(_St,FactortoObject), _pt,_St, Eval_times

def Further_Swap_Search(EvaluationFunction, Solution, p, node_resort_v, FactortoObject, CL, T_max, param, MonteCarloTimes, QuickCheckList,Eval_times,TemSolutionList,ConfidenceRecord,CostList,MonteCarloList):

    _St = np.copy(Solution)
    _c = solution_cost(_St,FactortoObject)
    _p = p
    node_list = [i for i in range(int(param[0]))]
    random.shuffle(node_list)
    
    # 遍历所有Node对
    for i in range(int(param[0])-1):
        node_id1 = node_list[i]
        for j in range(i + 1,int(param[0])):
            node_id2 = node_list[j]
            solution_group = []
            # 遍历value矩阵中比原value大的因子组合
            for factor_id1 in node_resort_v[node_id1]:
                for factor_id2 in node_resort_v[node_id2]:
                    S_temp = np.copy(_St)
                    S_temp[node_id1], S_temp[node_id2]= factor_id1, factor_id2
                    c_st = solution_cost(S_temp,FactortoObject)
                    if c_st < _c:
                        # 构造堆
                        heapq.heappush(solution_group,list([c_st,S_temp]))

            while solution_group: 
                # 默认弹出最小值，因为取负，所以是比当前解cost小的最大值
                temp = heapq.heappop(solution_group)
                # _pt, e = confidence_list_evaluation(ConfidenceRecord, EvaluationFunction, temp[1], T_max, FactortoObject, CL, param, MonteCarloTimes, QuickCheckList)
                _pt = Solution_Evaluation(EvaluationFunction, temp[1], T_max, FactortoObject, CL, param, MonteCarloTimes, QuickCheckList)
                Eval_times += 1
                if _pt >= CL:
                    _St = np.copy(temp[1])   # 更新最优解
                    _p = _pt
                    _c = temp[0]
                    FeasibleSolutionList(_St,_c,_p,CostList,MonteCarloList)
                    TemSolutionList.append([_c,_p,_St,Eval_times])
                    break       # 不再继续评估当前class组合，开始下一组class

    feasible_Solution = np.copy(_St)
    obj_cost = solution_cost(_St,FactortoObject)
    p = _p
    # print(f"The Evaluation times of further swap search procedure is {Eval_times}")

    return  obj_cost, p, feasible_Solution, Eval_times

def FeasibleSolutionList(Solution,cost,ConfidenceLevel,CostQueue,MonteCarloQueue):
    def push_Cost(queue,Solution,cost):
        # queue格式：[(cost,factor,...),(cost,factor,...),...]
        Queue_size = 30
        Solution.insert(0,-cost)    # heap 默认弹出最小value, 取负
        if Solution not in queue:
            if len(queue) < Queue_size:
                    heapq.heappush(queue, Solution)
            else:
                heapq.heappushpop(queue, Solution)

    def push_MonteCarlo(queue,Solution,cost,ConfidenceLevel):
        # queue格式：[tuple(MC_p,cost,factor,...),tuple(MC_p,cost,factor,...),...]
        Queue_size = 30
        cost_solu_list = []

        for q in queue:
            cost_solu_list.append(q[1:])
        Solution.insert(0,cost)

        if tuple(Solution) not in cost_solu_list:       #判断是否已在队列中
            Solution.insert(0,ConfidenceLevel)
            queue.append(tuple(Solution))
            if len(queue) > Queue_size:                     #队列溢出，剔除一个
                queue.sort(key=lambda x:(-x[0],x[1]))
                queue.pop()
        else:
            pass

    push_MonteCarlo(MonteCarloQueue,list(np.copy(Solution)),cost,ConfidenceLevel)
    push_Cost(CostQueue,list(np.copy(Solution)),cost)

def UpdateFeasibleSolutionList(Clist,Mlist,ConfidenceRecordList, EvaluationFunction, T_max, FactortoObject, ConfidenceLevel, param, MonteCarloTimes, QuickCheckList, Eval_t):
    New_CostList = heapq.nlargest(len(Clist),Clist)
    for i in range(len(New_CostList)):
        New_CostList[i][0] = -New_CostList[i][0]
        for _ in range(2):
            # _p, e = confidence_list_evaluation(ConfidenceRecordList, EvaluationFunction, New_CostList[i][1:], T_max, FactortoObject, ConfidenceLevel, param, MonteCarloTimes, QuickCheckList)
            _p = Solution_Evaluation(EvaluationFunction, New_CostList[i][1:], T_max, FactortoObject, ConfidenceLevel, param, MonteCarloTimes, QuickCheckList)
            Eval_t += 1
        New_CostList[i].insert(1,_p)

    New_MonteCarloList = heapq.nlargest(len(Mlist),Mlist)
    New_MonteCarloList = [list(NM) for NM in New_MonteCarloList]
    for j in range(len(New_MonteCarloList)):
        for _ in range(2):
            # _p, e = confidence_list_evaluation(ConfidenceRecordList, EvaluationFunction, New_MonteCarloList[j][2:], T_max, FactortoObject, ConfidenceLevel, param, MonteCarloTimes, QuickCheckList)
            _p = Solution_Evaluation(EvaluationFunction, New_MonteCarloList[j][2:], T_max, FactortoObject, ConfidenceLevel, param, MonteCarloTimes, QuickCheckList)
            Eval_t += 1
        New_MonteCarloList[i][0] = _p
    New_MonteCarloList.sort(reverse=True)   # 按评估的置信度从大到小排列

    return New_CostList, New_MonteCarloList, Eval_t

def Local_Search_DD(EvaluationFunction, S_cp, node_resort_v, FactortoObject, ConfidenceLevel, T_max, param, MaxIter, MonteCarloTimes, QuickCheckList):
    S_opt,_St = np.copy(S_cp[0]),np.copy(S_cp[0])
    c_opt,_ct = S_cp[1],S_cp[1]
    _p,_pt = S_cp[2],S_cp[2]
    t = 0
    Eval_times = S_cp[3]
    Tem_solution = S_cp[4]
    ConfidenceRecordList = np.ones(2+int(param[0]))
    MonteCarloList = []
    CostList = []
    #----------- 初始化ConfidenceRecordList, MonteCarloList, CostList -----------
    s_list = [1,_p]
    s_list.extend(S_opt)
    ConfidenceRecordList = np.vstack((ConfidenceRecordList,s_list))
    FeasibleSolutionList(S_opt,c_opt,_p,CostList,MonteCarloList)

    while t < MaxIter:
        _ct,_pt,_St,Eval_times = Local_Swap_Search(EvaluationFunction, _St, _pt, node_resort_v, FactortoObject, ConfidenceLevel, T_max, param, MonteCarloTimes, QuickCheckList,Eval_times,Tem_solution,ConfidenceRecordList, CostList,MonteCarloList)
        # print(f"Local_Swap_Search: {[_St,_ct,_pt,eva]}")
        if _ct < c_opt:
            S_opt = np.copy(_St)
            c_opt = _ct
            _p = _pt
            FeasibleSolutionList(S_opt,c_opt,_p,CostList,MonteCarloList)
        ex_node=[]
        ex_factor = [factor for factor in _St] # 禁忌集初始化
        _ct,_pt,_St,eva = Degrade_(EvaluationFunction, _St, _pt, node_resort_v,FactortoObject, ConfidenceLevel, T_max, param, MonteCarloTimes, ex_node, ex_factor, QuickCheckList, ConfidenceRecordList)
        FeasibleSolutionList(_St,_ct,_pt,CostList,MonteCarloList)
        Eval_times += eva
        t += 1

    c_opt,_p,S_opt,Eval_times = Further_Swap_Search(EvaluationFunction, S_opt, _p, node_resort_v, FactortoObject, ConfidenceLevel, T_max, param, MonteCarloTimes, QuickCheckList,Eval_times,Tem_solution,ConfidenceRecordList, CostList,MonteCarloList)
    # print(f"-------------- Optimal: {S_opt},{c_opt},{_p}")
    FeasibleSolutionList(S_opt,c_opt,_p,CostList,MonteCarloList)
    CostList,MonteCarloList,Eval_times = UpdateFeasibleSolutionList(CostList,MonteCarloList,ConfidenceRecordList, EvaluationFunction, T_max, FactortoObject, ConfidenceLevel, param, MonteCarloTimes, QuickCheckList, Eval_times)
    
    # 原始输出：最小cost
    Optimal_Solution = CostList[0][2:]
    Optimal_cost = CostList[0][0]
    Optimal_p = CostList[0][1]
    Optimal_0 = [Optimal_cost,Optimal_p,Optimal_Solution]

    # 变体1：以0.995为置信度阈值输出
    maxP = 0
    for CostSolution in CostList:
        if CostSolution[1] >= maxP:
            sub_cost = CostSolution[0]
            maxP = CostSolution[1]
            sub_Solution = CostSolution[2:]
                 
        if CostSolution[1] >= UpConfidenceLevel:       # 若遇到置信度大于0.995的解 
            Optimal_cost = CostSolution[0]
            maxP = CostSolution[1]
            Optimal_p = CostSolution[1]
            Optimal_Solution = CostSolution[2:]
            break
        
    if maxP < UpConfidenceLevel:  # 若解集没有符合条件的解，则取遇到的最大置信度的为输出解
        Optimal_Solution = sub_Solution
        Optimal_cost = sub_cost
        Optimal_p = maxP
    
    Optimal_1 = [Optimal_cost,Optimal_p,Optimal_Solution]
    
    # 变体3： 输出Cost解集中的前十个
    Optimal_3 = CostList[:10]

    # 变体2： 两个解集，加权输出
    CostOnlySolution = [s[2:] for s in CostList]
    MonteCarloOnlySolution = [list(s[2:]) for s in MonteCarloList]
    TS = CostOnlySolution + MonteCarloOnlySolution # 合并两个集合的解
    TotalSolution = []
    [TotalSolution.append(x) for x in TS if x not in TotalSolution]    # 去除重复元素
    TotalScore = [0 for _ in range(len(TotalSolution))]
    WholeSolution = []

    for s in range(len(TotalSolution)):
        CostScore = 0
        MonteCarloScore = 0
        if TotalSolution[s] in CostOnlySolution:
            _index =  CostOnlySolution.index(TotalSolution[s])
            CostScore = 30 - _index
            _p = CostList[_index][1]
            _c = CostList[_index][0]
        if TotalSolution[s] in MonteCarloOnlySolution:
            _index =  MonteCarloOnlySolution.index(TotalSolution[s])
            MonteCarloScore = 30 -_index
            _p = MonteCarloList[_index][0]
            _c = MonteCarloList[_index][1]
        TotalScore[s] = _alpha * CostScore + (1-_alpha) * MonteCarloScore
        WholeSolution.append([TotalScore[s], _c, _p] + TotalSolution[s])

    WholeSolution.sort()
    Optimal_Solution = WholeSolution[-1][3:]
    Optimal_cost = WholeSolution[-1][1]
    Optimal_p = WholeSolution[-1][2]
    Optimal_2 = [Optimal_cost,Optimal_p,Optimal_Solution]
    # Optimal_2 =[WholeSolution1[-1][1:],WholeSolution2[-1][1:],WholeSolution3[-1][1:],WholeSolution4[-1][1:]]

    return  Optimal_0, Optimal_1, Optimal_2, Optimal_3, Eval_times,Tem_solution
