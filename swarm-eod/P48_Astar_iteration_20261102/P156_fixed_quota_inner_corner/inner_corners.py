def _corners(memory,allowed,xx,yy,radius):
    """Harris proposes pivots; two actual perpendicular hit arms certify them.

    No true map, map-name coordinates, or synthetic frame evidence is used.
    This axis-aligned rule deliberately abstains on unsupported/diagonal walls.
    """
    measured=cv2.resize((np.asarray(memory.hits)>=2).astype(np.float32),
                        (allowed.shape[1],allowed.shape[0]),interpolation=cv2.INTER_AREA)>0
    response=cv2.cornerHarris(measured.astype(np.float32),3,3,.04)
    if not response.size or float(response.max())<=0:return []
    peaks=(response==cv2.dilate(response,np.ones((5,5),np.uint8)))&(response>.05*response.max())
    rows,cols=np.nonzero(peaks);out=[]
    lock=getattr(memory,'corner_cluster_anchor',None)
    for peak_row,peak_col in zip(rows,cols):
        certified=[]
        # A 3x3 Harris response peak may be offset from the measured junction.
        # Snap only to a measured cell in its two-cell filter support, then
        # require both long arms; a lone segment endpoint still cannot pass.
        for row in range(max(0,peak_row-2),min(measured.shape[0],peak_row+3)):
            for col in range(max(0,peak_col-2),min(measured.shape[1],peak_col+3)):
                if not measured[row,col]:continue
                arms=[]
                for dr,dc in[(0,1),(0,-1),(1,0),(-1,0)]:
                    support=[]
                    for distance in range(2,7):
                        rr,cc=row+dr*distance,col+dc*distance
                        r0,r1=max(0,rr-1),min(measured.shape[0],rr+2)
                        c0,c1=max(0,cc-1),min(measured.shape[1],cc+2)
                        support.append(r0<r1 and c0<c1 and measured[r0:r1,c0:c1].any())
                    arms.append(sum(support)>=4)
                if any(arms[:2])and any(arms[2:]):certified.append(((row-peak_row)**2+(col-peak_col)**2,row,col))
        if not certified:continue
        _,row,col=min(certified)
        pivot=np.array([xx[row,col],yy[row,col]])
        # Internal pivots only; outer corners already failed the majority test.
        if min(memory.width/2-abs(pivot[0]),memory.height/2-abs(pivot[1]))<3*memory.CELL:continue
        if lock is not None and np.linalg.norm(pivot-np.asarray(lock[:2]))>3*memory.CELL:continue
        arms=[]
        for dr,dc in[(0,1),(0,-1),(1,0),(-1,0)]:
            support=[]
            for distance in range(2,7):
                rr,cc=row+dr*distance,col+dc*distance
                r0,r1=max(0,rr-1),min(measured.shape[0],rr+2)
                c0,c1=max(0,cc-1),min(measured.shape[1],cc+2)
                support.append(r0<r1 and c0<c1 and measured[r0:r1,c0:c1].any())
            arms.append(sum(support)>=4)
        if not(any(arms[:2])and any(arms[2:])):continue
        ids=np.flatnonzero(allowed & ((xx-pivot[0])**2+(yy-pivot[1])**2<=(4*memory.CELL)**2))
        if not len(ids):continue
        if lock is None:
            flat=min(ids,key=lambda n:(float((xx.ravel()[n]-pivot[0])**2+(yy.ravel()[n]-pivot[1])**2),int(n)))
            anchor=np.array([xx.ravel()[flat],yy.ravel()[flat]])
        else:anchor=np.asarray(lock[2:4],float)
        region=allowed & ((xx-anchor[0])**2+(yy-anchor[1])**2<=(CORNER_RADIUS_RATIO*radius)**2)
        # One connected free pocket; no gathering through a dividing wall.
        count,labels=cv2.connectedComponents(region.astype(np.uint8),connectivity=8)
        cell=memory.world_to_cell(anchor);component=int(labels[cell])
        if component==0:continue
        region &= labels==component
        if any(np.linalg.norm(anchor-old[2])<3*memory.CELL for old in out):continue
        out.append((float(pivot[0]),float(pivot[1]),anchor,region))
    return out
